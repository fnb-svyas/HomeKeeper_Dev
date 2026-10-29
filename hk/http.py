"""HTTP access: one identifying User-Agent, timeouts, on-disk cache, offline fixtures.

Design rules (from the audit):
  * NWS and Nominatim require an identifying User-Agent; everyone else tolerates it.
  * Every response is cached to cache/<sha1>.json with the retrieval timestamp so a
    profile can record `retrieved_date` and so repeated runs don't re-hit public APIs.
  * Offline mode never touches the network: it answers from fixtures (synthetic, for
    demos/tests) or from the cache, and otherwise returns a FetchResult with ok=False
    and a plain reason. Unknown must stay visible, never silently default.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

from . import CACHE, DATA

USER_AGENT = "HomeKeeper-prototype/0.2 (personal research pilot; contact set in config)"
DEFAULT_TIMEOUT = 25
_MIN_INTERVAL = 1.0  # polite: at most ~1 request/second to any host
_last_call: dict[str, float] = {}

# Fixture registry: offline mode maps a (method, url-prefix) to a fixture payload.
_fixtures: list[tuple[str, str, object]] = []
OFFLINE = False


def set_offline(flag: bool) -> None:
    global OFFLINE
    OFFLINE = bool(flag)


def register_fixture(method: str, url_prefix: str, payload) -> None:
    """Register a synthetic response for offline runs. First prefix match wins."""
    _fixtures.append((method.upper(), url_prefix, payload))


def clear_fixtures() -> None:
    _fixtures.clear()


@dataclass
class FetchResult:
    ok: bool
    url: str
    status: Optional[int] = None
    data: object = None            # parsed JSON (or text if not JSON)
    retrieved: Optional[str] = None  # ISO timestamp (UTC) of actual retrieval
    from_cache: bool = False
    from_fixture: bool = False
    reason: str = ""
    extra: dict = field(default_factory=dict)


def _cache_path(key: str) -> pathlib.Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _throttle(url: str) -> None:
    host = urllib.parse.urlparse(url).netloc
    last = _last_call.get(host, 0.0)
    wait = _MIN_INTERVAL - (time.time() - last)
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.time()


_ssl_ctx = None


def ssl_context() -> ssl.SSLContext:
    """System trust store plus any public CA certificates bundled under data/certs/.

    Some public GIS servers (PASDA) do not send their intermediate certificate, so Python
    cannot build the chain. tools/fix_pasda_tls.py saves that intermediate here; verification
    stays fully on — a certificate is still only trusted if it chains to a system root.
    """
    global _ssl_ctx
    if _ssl_ctx is None:
        ctx = ssl.create_default_context()
        for pem in sorted((DATA / "certs").glob("*.pem")) if (DATA / "certs").exists() else []:
            try:
                ctx.load_verify_locations(cafile=str(pem))
            except ssl.SSLError:
                pass
        _ssl_ctx = ctx
    return _ssl_ctx


def _parse(body: bytes):
    text = body.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except ValueError:
        return text


def fetch(url: str, *, method: str = "GET", data: Optional[dict] = None,
          headers: Optional[dict] = None, max_age_days: Optional[float] = 30,
          timeout: int = DEFAULT_TIMEOUT) -> FetchResult:
    """GET or form-POST `url`. Honors offline mode, fixtures and the on-disk cache."""
    method = method.upper()
    key = method + " " + url + ("" if not data else " " + urllib.parse.urlencode(sorted(data.items())))

    # 1. fixtures (synthetic) — only in offline mode
    if OFFLINE:
        for m, prefix, payload in _fixtures:
            if m == method and url.startswith(prefix):
                return FetchResult(True, url, 200, payload, _now(), from_fixture=True,
                                   reason="synthetic fixture (offline demo)")

    # 2. cache
    cp = _cache_path(key)
    if cp.exists():
        try:
            entry = json.loads(cp.read_text(encoding="utf-8"))
            age_days = (time.time() - entry["ts"]) / 86400.0
            if OFFLINE or max_age_days is None or age_days <= max_age_days:
                return FetchResult(True, url, entry.get("status", 200), entry["data"],
                                   entry["retrieved"], from_cache=True)
        except (ValueError, KeyError):
            pass

    if OFFLINE:
        return FetchResult(False, url, reason="offline: no fixture or cached response for this request")

    # 3. network
    hdrs = {"User-Agent": USER_AGENT, "Accept": "application/json, application/geo+json, */*"}
    if headers:
        hdrs.update(headers)
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    _throttle(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as resp:
            status = resp.getcode()
            parsed = _parse(resp.read())
    except urllib.error.HTTPError as e:
        return FetchResult(False, url, e.code, reason=f"HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        return FetchResult(False, url, reason=f"network error: {e.reason}")
    except (TimeoutError, OSError) as e:
        return FetchResult(False, url, reason=f"network error: {e}")

    retrieved = _now()
    try:
        cp.write_text(json.dumps({"ts": time.time(), "retrieved": retrieved, "status": status,
                                  "url": url, "data": parsed}), encoding="utf-8")
    except (OSError, TypeError):
        pass
    return FetchResult(True, url, status, parsed, retrieved)


def q(url: str, params: dict) -> str:
    """Append query parameters (values already stringified)."""
    sep = "&" if "?" in url else "?"
    return url + sep + urllib.parse.urlencode(params, safe="(),*':$=")
