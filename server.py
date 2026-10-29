#!/usr/bin/env python3
"""HomeKeeper local web app — single entry point, standard library only.

  python server.py              # http://127.0.0.1:8765
  python server.py --port 9000
  python server.py --snapshot   # writes a read-only synthetic snapshot to demos/snapshot.html and exits

Binds to 127.0.0.1 only: the app is for this computer. House records are JSON files under houses/.
Nothing runs in the background; reminders are a calendar file you download.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import pathlib
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from hk import actions, briefs, browse, budget, records, score, builder, http as hk_http, landing, questions, reminders, rules, samples, web, web2, web3  # noqa: E402
from hk.evidence import Field, Profile, slug  # noqa: E402

FLASH: dict[str, str] = {}


def _flash_key(loc: str) -> str:
    """Flash messages belong to a house, not to a particular URL/anchor under it."""
    path = loc.split("?")[0].split("#")[0]
    parts = [x for x in path.split("/") if x]
    return "/house/" + parts[1] if len(parts) >= 2 and parts[0] == "house" else path


def _profile(hid: str) -> Profile | None:
    try:
        return Profile.load(hid)
    except FileNotFoundError:
        return None


def _benchmark(p: Profile) -> None:
    """Comparable-sales benchmark for the price part of the Ownership Score (fetched once, cached 30 days)."""
    p.set(records.price_benchmark(p, score.config()["price"]), reason="comparable-sales benchmark")
    p.save()


def _task(p: Profile, rid: str):
    return next((t for t in rules.evaluate(p) if t.rule_id == rid), None)


def _num(s: str | None):
    try:
        return float(s) if s not in (None, "") else None
    except ValueError:
        return None


class Handler(BaseHTTPRequestHandler):
    server_version = "HomeKeeper/0.8"

    def log_message(self, fmt, *args):  # quieter console
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    # ---- helpers
    def _send(self, body: str, status: int = 200, ctype: str = "text/html; charset=utf-8", extra: dict | None = None):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def _redirect(self, loc: str, msg: str = ""):
        if msg:
            FLASH[_flash_key(loc)] = msg
        self.send_response(303); self.send_header("Location", loc); self.send_header("Content-Length", "0"); self.end_headers()

    def _form(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n).decode("utf-8") if n else ""
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw, keep_blank_values=True).items()}

    def _flash(self, path: str) -> str:
        return FLASH.pop(_flash_key(path), "")

    # ---- GET
    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        parts = [x for x in u.path.split("/") if x]
        qs = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            if not parts:
                return self._send(landing.landing_page())
            if parts == ["owner"]:
                return self._send(web2.landing(Profile.list_ids(), self._flash("/owner")))
            if parts == ["browse"]:
                return self._send(browse.browse_index(browse.recents(Profile.list_ids()), self._flash("/browse")))
            if parts[0] == "browse" and len(parts) == 2:
                p = _profile(parts[1])
                if p is None or p.value("stage") != "before_buy":
                    return self._send("no such home in Browse Homes", 404, "text/plain")
                if "price_benchmark" not in p.fields and not p.synthetic:
                    _benchmark(p)
                return self._send(browse.browse_property(p, browse.recents(Profile.list_ids()), self._flash("/browse/" + p.house_id)))
            if parts[0] != "house" or len(parts) < 2:
                return self._send("not found", 404, "text/plain")
            p = _profile(parts[1])
            if p is None:
                return self._send("no such house", 404, "text/plain")
            sub = parts[2] if len(parts) > 2 else ""
            base = f"/house/{p.house_id}"
            if sub == "" and p.value("stage") == "before_buy":
                return self._redirect("/browse/" + p.house_id)
            if sub == "":
                return self._send(web3.house_page(p, self._flash(base), open_task=qs.get("open", "")))
            if sub == "start":
                return self._send(web2.onboarding(p, self._flash(base + "/start")))
            if sub == "tasks":
                return self._redirect(base + "#now")
            if sub == "house":
                return self._redirect(base + "#house")
            if sub == "money":
                return self._send(web2.money_page(p, self._flash(base + "/money")))
            if sub == "history":
                return self._send(web2.history_page(p, self._flash(base + "/history")))
            if sub == "report" and len(parts) > 3:
                return self._send(web2.report_page(p, parts[3]))
            if sub in ("plan", "budget", "reports", "record"):  # old addresses
                return self._redirect({"plan": base + "#now", "budget": base + "/money", "reports": base + "/report/buy", "record": base + "#house"}[sub])
            if sub == "fit":
                return self._send(web.fit_page(p, _num(qs.get("hours")) or 2.0, _num(qs.get("dollars")) if qs.get("dollars") not in (None, "") else 200.0))
            if sub == "providers" and len(parts) > 3:
                t = _task(p, parts[3])
                return self._send(web.providers_page(p, t)) if t else self._send("no such task", 404, "text/plain")
            if sub == "brief" and len(parts) > 3:
                t = _task(p, parts[3])
                return self._send(web.brief_page(p, t)) if t else self._send("no such task", 404, "text/plain")
            if sub == "reminders.ics":
                return self._send(reminders.to_ics(p, reminders.build_events(p)), 200, "text/calendar; charset=utf-8",
                                  {"Content-Disposition": f'attachment; filename="homekeeper-{p.house_id}.ics"'})
            if sub == "export.json":
                return self._send(json.dumps(p.to_dict(), indent=2), 200, "application/json",
                                  {"Content-Disposition": f'attachment; filename="homekeeper-{p.house_id}.json"'})
            return self._send("not found", 404, "text/plain")
        except Exception as ex:  # show the error rather than a blank page
            return self._send(web.page("Error", f"<h1>Something went wrong</h1><pre class='doc'>{web.e(type(ex).__name__)}: {web.e(ex)}</pre><p><a href='/'>Back to houses</a></p>"), 500)

    # ---- POST
    def do_POST(self):
        u = urllib.parse.urlparse(self.path)
        parts = [x for x in u.path.split("/") if x]
        f = self._form()
        try:
            if parts == ["build"]:
                addr = f.get("address", "").strip()
                browsing = f.get("mode") == "browse"
                if not addr:
                    return self._redirect("/browse" if browsing else "/owner", "Type an address to start.")
                if browsing:
                    # Browse records live under their own ids, so a lookup never touches a homeowner's record.
                    p = builder.build(addr, house_id="browse-" + slug(addr))
                    builder.apply_answer(p, "stage", "before_buy", reason="looked up from Browse Homes")
                    _benchmark(p)
                    return self._redirect(f"/browse/{p.house_id}")
                existing = _profile(slug(addr))
                if existing is not None and existing.value("stage") != "before_buy":
                    return self._redirect(f"/house/{existing.house_id}", "You already have this house; here it is. Nothing was overwritten.")
                p = builder.build(addr)
                return self._redirect(f"/house/{p.house_id}/start")
            if parts == ["sample"]:
                name = f.get("name", "complete")
                if name not in samples.SAMPLES:
                    return self._redirect("/", "Unknown sample.")
                addr = samples.install(name)
                browsing = f.get("mode") == "browse"
                p = builder.build(addr, house_id=("browse-sample-" if browsing else "sample-") + name, mode="offline-sample", synthetic=True)
                if browsing:
                    _benchmark(p)  # from the SYNTHETIC comparable-sales fixtures
                hk_http.set_offline(False); hk_http.clear_fixtures()
                if browsing:
                    builder.apply_answer(p, "stage", "before_buy", reason="example opened from Browse Homes")
                    return self._redirect(f"/browse/{p.house_id}", "An invented example: the address and its records don't exist.")
                return self._redirect(f"/house/{p.house_id}", "Demo house created. Everything here is invented.")
            if parts[0] == "browse" and len(parts) == 3 and parts[2] == "choose":
                p = _profile(parts[1])
                if p is None or p.value("stage") != "before_buy":
                    return self._send("no such home in Browse Homes", 404, "text/plain")
                p2 = builder.build(p.address_input, house_id=p.house_id, mode=p.mode, synthetic=p.synthetic, choose=int(f.get("choose", 0)))
                builder.apply_answer(p2, "stage", "before_buy", reason="looked up from Browse Homes")
                if not p2.synthetic:
                    _benchmark(p2)
                return self._redirect(f"/browse/{p2.house_id}", "Property chosen.")
            if parts[0] == "browse" and len(parts) == 3 and parts[2] == "inputs":
                p = _profile(parts[1])
                if p is None or p.value("stage") != "before_buy":
                    return self._send("no such home in Browse Homes", 404, "text/plain")
                back = f"/browse/{p.house_id}#score"
                before = score.compute(p)["overall"]
                price = None
                if f.get("action") != "clear":
                    try:
                        price = score.parse_price(f.get("asking_price", ""))
                    except ValueError:
                        return self._redirect(back, f"Couldn't read {f.get('asking_price')!r} as a price. Try a number like 345000.")
                score.set_inputs(p, asking_price=price, hoa_exterior=f.get("hoa_exterior", "unknown"),
                                 clear_price=f.get("action") == "clear")
                p.save()
                after = score.compute(p)["overall"]
                msg = ("Score updated: " + (str(after) if after is not None else "withheld") +
                       (" (was " + (str(before) if before is not None else "withheld") + ")." if before != after else ", unchanged."))
                return self._redirect(back, msg)
            if parts[0] != "house" or len(parts) < 3:
                return self._send("not found", 404, "text/plain")
            p = _profile(parts[1])
            if p is None:
                return self._send("no such house", 404, "text/plain")
            base = f"/house/{p.house_id}"
            act = parts[2]
            before = {t.rule_id: t.status for t in rules.evaluate(p)}

            def changed_msg(prefix: str) -> str:
                after = {t.rule_id: t.status for t in rules.evaluate(p)}
                ch = [f"{r}: {before.get(r, '—')} → {after[r]}" for r in after if before.get(r) != after[r]]
                ch += [f"{r}: {before[r]} → —" for r in before if r not in after]
                return prefix + (" Recommendations changed: " + "; ".join(ch) if ch else " No recommendation changed.")

            nxt = {"today": base, "now": base + "#now", "tasks": base + "#now", "onboard": base + "/start", "house": base + "#house"}.get(f.get("next", ""), base)
            back = (base + "?open=" + f["back"] + "#" + f["back"]) if f.get("back") else None
            if act == "choose":
                p2 = builder.build(p.address_input, house_id=p.house_id, mode=p.mode, synthetic=p.synthetic, choose=int(f.get("choose", 0)))
                return self._redirect(base + "/start", "Address recorded.")
            if act == "answer":
                field, raw = f.get("field", ""), f.get("value", "")
                kind = next((k for n, _, _, k in questions.ONBOARDING if n == field), "text")
                if raw.strip() == "" and f.get("next") == "onboard":
                    return self._redirect(nxt)
                try:
                    val = questions.parse_answer(kind, raw)
                except ValueError as ex:
                    return self._redirect(nxt, f"Could not read {raw!r} as {kind}: {ex}")
                builder.apply_answer(p, field, val, reason=f.get("reason") or "answered in the app")
                label = next((q for n, q, _, _ in questions.ONBOARDING if n == field), field.replace("_", " "))
                return self._redirect(nxt, changed_msg(f"Saved {label.rstrip('?').lower()}: {'unknown' if val is None else val}."))
            if act == "done":
                rid = f.get("task", ""); t = _task(p, rid)
                if not t:
                    return self._redirect(base + "/plan", f"No open task {rid}.")
                rv = next((r["version"] for r in rules.load_rules() if r["id"] == rid), 0)
                actions.complete(p, rid, date=f.get("date") or None, notes=f.get("notes", ""), cost=_num(f.get("cost")),
                                 contractor=f.get("contractor", ""), component=t.component, rule_version=rv)
                p.save()
                return self._redirect(back or nxt, f"[undo:{rid}]" + changed_msg(f"Done: {t.title}."))
            if act == "snooze":
                rid = f.get("task", "")
                until = f.get("until", "").strip()
                if not until and f.get("days", "").isdigit():
                    until = (_dt.date.today() + _dt.timedelta(days=int(f["days"]))).isoformat()
                if not until:
                    return self._redirect(back or base + "#now", "Pick a date to postpone until.")
                actions.snooze(p, rid, until, f.get("reason", "")); p.save()
                return self._redirect(back or base + "#now", f"[undo:{rid}]Postponed until {until}. It comes back on its own; it is not counted as done.")
            if act == "dismiss":
                rid = f.get("task", "")
                actions.does_not_apply(p, rid, f.get("reason", "")); p.save()
                return self._redirect(back or base + "#now", f"[undo:{rid}]Set aside (\"{f.get('reason', '')}\"). Kept in the record, not counted as done. If a house fact is wrong, edit it in The house section instead.")
            if act == "reopen":
                actions.reopen(p, f.get("task", ""), f.get("reason", "")); p.save()
                return self._redirect(back or base + "#now", changed_msg("Brought back."))
            if act == "undo":
                rid = f.get("task", "")
                what = actions.undo(p, rid); p.save()
                return self._redirect(base + "#" + rid, f"Undone ({what})." if what else "Nothing to undo for that task.")
            if act == "equipment":
                yr = int(f["year"]) if f.get("year", "").strip().isdigit() else None
                e_ = p.add_equipment(f.get("component", ""), make=f.get("make", ""), model=f.get("model", ""), installed_year=yr,
                                     manual_source_id=f.get("manual") or None)
                if yr and f.get("component") in ("roof", "water_heater", "furnace", "ac", "sump_pump"):
                    p.correct(f"{f['component']}_installed_year", yr, source_id=f"equipment:{e_['id']}", reason="from equipment record", status="owner_confirmed")
                if yr and yr >= _dt.date.today().year:
                    p.correct("new_equipment_pending_registration", True, reason="current-year install", status="owner_confirmed")
                p.save()
                return self._redirect(base + "#house", changed_msg(f"Saved the {f.get('component', '').replace('_', ' ')}."))
            if act == "finding":
                p.add_finding(f.get("component", ""), f.get("severity", "info"), f.get("description", ""),
                              source_doc=f.get("source") or "inspection report", observed_date=f.get("date") or None)
                p.save()
                return self._redirect(base + "#now", changed_msg("Finding saved — it is now in your list."))
            if act == "responsibility":
                party = f.get("party", "").strip()
                p.set_responsibility(f.get("component", ""), None if party.lower() in ("homeowner", "me", "none") else party, f.get("reason", ""))
                p.save()
                return self._redirect(base + "#house", changed_msg("Saved."))
            if act == "quote":
                budget.add_estimate(p, applies_to=f.get("applies_to", ""), low=_num(f.get("low")) or 0, high=_num(f.get("high")) or 0,
                                    basis=f.get("basis", "user_quote"), scope=f.get("scope", ""), exclusions=f.get("exclusions", ""),
                                    source=f.get("source", ""))
                p.save()
                return self._redirect(base + "/money", "Estimate saved.")
            if act == "reserve":
                budget.set_reserve(p, component=f.get("component", ""), years=int(f.get("years") or 5), low=_num(f.get("low")) or 0,
                                   high=_num(f.get("high")) or 0, basis=f.get("basis", "planning_assumption"))
                p.save()
                return self._redirect(base + "/money", "Scenario saved.")
            if act == "document":
                actions.add_document(p, kind=f.get("kind", "other"), title=f.get("title", ""), ref=f.get("ref", ""), component=f.get("component", ""))
                p.save()
                return self._redirect(base + "#history", "Document reference saved.")
            if act == "brief":
                t = _task(p, f.get("task", ""))
                if t:
                    path = briefs.write_brief(p, t); p.save()
                    return self._redirect(base + "/tasks", f"Brief saved: {path}")
                return self._redirect(base + "/tasks", "No such task.")
            if act == "purge":
                n = actions.purge_private(p); p.save()
                return self._redirect(base + "#house", f"Private information removed: {n}")
            return self._send("not found", 404, "text/plain")
        except Exception as ex:
            return self._send(web.page("Error", f"<h1>That action did not complete</h1><pre class='doc'>{web.e(type(ex).__name__)}: {web.e(ex)}</pre><p><a href='javascript:history.back()'>Go back</a></p>"), 500)


def write_snapshot(out: pathlib.Path) -> pathlib.Path:
    """A single read-only HTML file built from the synthetic sample. Safe to publish: no real data."""
    import subprocess
    root = pathlib.Path(__file__).resolve().parent
    subprocess.run(["sh", str(root / "demos" / "run_checkpoint5_demo.sh")], capture_output=True)
    p = Profile.load("sample-complete")
    p.synthetic = True
    sections = [web3.house_page(p, snapshot=True)]
    # stitch the <main> bodies into one page with anchors; strip forms (simulated)
    import re
    mains = [re.search(r"<main>(.*)</main>", s, re.S).group(1) for s in sections]
    mains = [re.sub(r"<form.*?</form>", "<span class='limits'>[form — available in the local app]</span>", m, flags=re.S) for m in mains]
    labels = ["Demo house"]
    nav = "".join(f'<a href="#s{i}">{l}</a>' for i, l in enumerate(labels))
    body = "".join(f'<section id="s{i}"><hr style="border:0;border-top:2px solid var(--ink);margin:3rem 0 1rem"><p class="limits">{l}</p>{m}</section>' for i, (l, m) in enumerate(zip(labels, mains)))
    html = web3.page("HomeKeeper — synthetic demo snapshot", body, snapshot=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--snapshot", action="store_true", help="write demos/snapshot.html from the synthetic sample and exit")
    a = ap.parse_args(argv)
    if a.snapshot:
        print("wrote", write_snapshot(pathlib.Path(__file__).resolve().parent / "demos" / "snapshot.html"))
        return
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"HomeKeeper local app: http://127.0.0.1:{a.port}   (Ctrl+C to stop)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")


if __name__ == "__main__":
    main()
