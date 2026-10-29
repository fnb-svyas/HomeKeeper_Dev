"""Provider inventory and matching (Checkpoint 6).

Evidence categories are kept separate and worded literally (section 3 of the brief):
  existence       - a public list or the owner says the business exists
  task_suitability- the category the source lists them under (plumber, electrician, radon mitigator...)
  service_area    - municipalities or radius they say they serve; unknown unless evidenced
  registration    - PA HICPA registration (manual check; number + date)
  licensing       - ACHD registered master plumber; City of Pittsburgh trade license; PA DEP radon certification
  insurance       - only as a dated "insurance expiration on file" from City data, or a certificate the owner saw
  workmanship     - none available from any permitted source; shown as unknown

Ranking (brief 4G): task suitability -> serves the address -> relevant verified credentials ->
verification freshness -> distance. Unknown factors sort last within their tier and are displayed as unknown.

Store: data/providers/providers.json. Importers write records with source_id + checked date.
A record with synthetic=True is demo-only and is never shown for a real (non-sample) house.
"""
from __future__ import annotations

import csv
import io
import json
import math
import pathlib
import time
from typing import Optional

from . import DATA, http, sources
from .evidence import Profile, today
from .geocode import COUNTY_GEOCODER
from .rules import Task

PDIR = DATA / "providers"
STORE = PDIR / "providers.json"
WPRDC_API = "https://data.wprdc.org/api/action/datastore_search"
ACHD_PLUMBERS_RESOURCE = "60637ef7-96c9-47ee-95c3-ccc2a2140367"   # WPRDC "Allegheny County Plumbers" (CC0); fields discovered at import
CITY_TRADES_PACKAGE = "https://data.wprdc.org/api/action/package_show?id=business-contractors-trades"

CATEGORY_ALIASES = {"hvac": ["hvac", "heating", "furnace"], "plumber": ["plumber", "plumbing"], "electrician": ["electrician", "electrical"],
                    "roofer": ["roofer", "roofing"], "chimney": ["chimney", "sweep"], "radon": ["radon mitigator", "radon tester", "radon"],
                    "gutter": ["gutter"], "engineer": ["engineer", "structural"], "pest_control": ["pest", "wdi", "termite"],
                    "landscaper": ["landscap", "grading"], "duct_cleaner": ["duct"], "waterproofing": ["waterproof"], "lead_assessor": ["lead"]}

CREDENTIAL_WORDING = {
    "hicpa": "Registered with the PA Attorney General under HICPA, {identifier}, as checked {date}",
    "achd_master_plumber": "Allegheny County Health Department registered master plumber, {identifier} (list dated {date})",
    "pgh_trade_license": "City of Pittsburgh trade license {identifier}, status {status}, per City open data {date}",
    "pgh_insurance_expiry": "Insurance expiration date on file with the City of Pittsburgh: {status} (City data {date})",
    "padep_radon": "PA DEP certified radon {status}, DEP ID {identifier}, per DEP list dated {date}",
    "csia": "Listed as CSIA Certified Chimney Sweep on csia.org as checked {date}",
    "owner_saw_coi": "Owner viewed a certificate of insurance on {date} (not independently verified)",
}
LICENSE_TYPES = {"achd_master_plumber", "pgh_trade_license", "padep_radon"}


# ---------------------------------------------------------------- store
def load() -> list[dict]:
    if STORE.exists():
        return json.loads(STORE.read_text(encoding="utf-8")).get("providers", [])
    return []


def save(providers: list[dict]) -> None:
    PDIR.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps({"updated": today(), "count": len(providers), "providers": providers}, indent=2,
                                ensure_ascii=False), encoding="utf-8")


def upsert(providers: list[dict], rec: dict) -> dict:
    key = (rec.get("name", "").strip().lower(), (rec.get("source_key") or "").lower())
    for p in providers:
        if (p.get("name", "").strip().lower(), (p.get("source_key") or "").lower()) == key:
            p.update({k: v for k, v in rec.items() if v not in (None, "", [])})
            p.setdefault("credentials", [])
            for c in rec.get("credentials", []):
                if c not in p["credentials"]:
                    p["credentials"].append(c)
            return p
    rec.setdefault("id", f"p-{len(providers)+1:04d}")
    rec.setdefault("credentials", []); rec.setdefault("claims", []); rec.setdefault("categories", [])
    rec.setdefault("service_area", None); rec.setdefault("synthetic", False)
    providers.append(rec)
    return rec


def add_manual(providers: list[dict], *, name: str, categories: list[str], address: str = "", phone: str = "",
               service_area: Optional[list] = None, note: str = "", synthetic: bool = False) -> dict:
    rec = {"name": name, "categories": categories, "address": address, "phone": phone, "service_area": service_area,
           "source_id": "manual_directory", "source_key": "manual", "existence": {"basis": "owner-entered", "date": today()},
           "note": note, "synthetic": synthetic, "credentials": [], "claims": []}
    return upsert(providers, rec)


def add_credential(provider: dict, *, ctype: str, identifier: str = "", status: str = "", date: Optional[str] = None,
                   source_id: str = "", url: str = "", checked_by: str = "owner") -> dict:
    assert ctype in CREDENTIAL_WORDING, f"unknown credential type {ctype}; known: {sorted(CREDENTIAL_WORDING)}"
    c = {"type": ctype, "identifier": identifier, "status": status, "date": date or today(), "source_id": source_id,
         "url": url, "checked_by": checked_by}
    provider.setdefault("credentials", []).append(c)
    return c


def wording(c: dict) -> str:
    return CREDENTIAL_WORDING[c["type"]].format(identifier=c.get("identifier") or "(number not recorded)",
                                                status=c.get("status") or "", date=c.get("date") or "?")


# ---------------------------------------------------------------- importers (run on the pilot machine)
def discover_fields(resource_id: str) -> tuple[list[str], http.FetchResult]:
    r = http.fetch(http.q(WPRDC_API, {"resource_id": resource_id, "limit": "3"}), max_age_days=0)
    if r.ok and isinstance(r.data, dict) and r.data.get("success"):
        return [f["id"] for f in r.data["result"].get("fields", [])], r
    return [], r


def _pick(fields: list[str], *needles: str) -> Optional[str]:
    for n in needles:
        for f in fields:
            if n in f.lower():
                return f
    return None


def _fetch_all(resource_id: str, filters: Optional[dict] = None, limit: int = 10000) -> tuple[list[dict], http.FetchResult]:
    params = {"resource_id": resource_id, "limit": str(limit)}
    if filters:
        params["filters"] = json.dumps(filters)
    r = http.fetch(http.q(WPRDC_API, params), max_age_days=7)
    if r.ok and isinstance(r.data, dict) and r.data.get("success"):
        return r.data["result"].get("records", []), r
    return [], r


def _drop_source(providers: list[dict], source_id: str) -> int:
    before = len(providers)
    providers[:] = [p for p in providers if p.get("source_id") != source_id]
    return before - len(providers)


def import_achd_plumbers(providers: list[dict]) -> dict:
    """WPRDC 'Allegheny County Plumbers' (CC0). Verified fields (2026-10-29 on the pilot machine):
    _id, registration_number, first_name, last_name, city, zip_code — one row per registered master plumber
    (a person, not a business); no address or phone, so distance stays unknown. The dataset is frozen since
    2026-07-29 (undercounting notice); every record carries that date. Re-running replaces earlier ACHD imports."""
    fields, r = discover_fields(ACHD_PLUMBERS_RESOURCE)
    if not fields:
        return {"ok": False, "reason": r.reason or "no fields", "fields": []}
    expected = {"registration_number", "first_name", "last_name", "city", "zip_code"}
    if not expected.issubset(set(fields)):
        return {"ok": False, "reason": f"unexpected fields {fields}; expected {sorted(expected)} — update import_achd_plumbers", "fields": fields}
    recs, r2 = _fetch_all(ACHD_PLUMBERS_RESOURCE)
    dropped = _drop_source(providers, "achd_master_plumbers")
    n = 0
    merged = 0
    seen: dict[tuple, dict] = {}
    for row in recs:
        first, last = (row.get("first_name") or "").strip(), (row.get("last_name") or "").strip()
        reg = str(row.get("registration_number") or "").strip()
        if not (first or last) or not reg:
            continue
        name = f"{last}, {first}".strip(", ")
        base = ", ".join(x for x in ((row.get("city") or "").strip().title(), str(row.get("zip_code") or "").strip()) if x)
        rec = {"name": name, "categories": ["plumber"], "address": "", "base_city": base, "phone": "",
               "source_id": "achd_master_plumbers", "source_key": f"achd:{reg}",
               "existence": {"basis": "WPRDC Allegheny County Plumbers dataset (CC0) — individual registered master plumber", "date": "2026-07-29"},
               "service_area": None, "synthetic": False,
               "credentials": [{"type": "achd_master_plumber", "identifier": f"HP {reg}", "status": "listed", "date": "2026-07-29",
                                "source_id": "achd_master_plumbers", "url": "https://data.wprdc.org/dataset/allegheny-county-plumbers",
                                "checked_by": "import"}],
               "note": "Individual plumber from the county registry; business name, address and phone are not in the dataset."}
        key = (name.lower(), base.lower())
        if key in seen:  # same person listed under more than one registration number: keep one record, all numbers
            prev = seen[key]
            if rec["credentials"][0] not in prev["credentials"]:
                prev["credentials"].append(rec["credentials"][0])
            merged += 1
            continue
        seen[key] = upsert(providers, rec); n += 1
    return {"ok": True, "imported": n, "merged_duplicate_rows": merged, "replaced_previous": dropped, "fields": fields,
            "note": "ACHD list frozen 2026-07-29 (WPRDC notice: undercounting after software transition); re-check at eapps.alleghenycounty.us/Plumbing"}


def import_city_trade_licenses(providers: list[dict], *, resource_id: Optional[str] = None, field_map: Optional[dict] = None,
                               license_filter: str = "electric") -> dict:
    """City of Pittsburgh 'Licensed Businesses, Contractors & Trades' (CC0). Resource id discovered from the package
    (the Trade Licenses resource id was not verified in the audit)."""
    rid = resource_id
    if not rid:
        r = http.fetch(CITY_TRADES_PACKAGE, max_age_days=7)
        if not (r.ok and isinstance(r.data, dict) and r.data.get("success")):
            return {"ok": False, "reason": r.reason or "package_show failed"}
        res = r.data["result"].get("resources", [])
        cand = [x for x in res if "trade" in (x.get("name") or "").lower() and x.get("datastore_active")] or \
               [x for x in res if "contractor" in (x.get("name") or "").lower() and x.get("datastore_active")]
        if not cand:
            return {"ok": False, "reason": "no Trade/Contractor datastore resource in package", "resources": [x.get("name") for x in res]}
        rid = cand[0]["id"]
    fields, r = discover_fields(rid)
    if not fields:
        return {"ok": False, "reason": r.reason or "no fields", "resource_id": rid}
    fm = field_map or {"name": _pick(fields, "business_name", "name"), "type": _pick(fields, "license_type", "type"),
                       "state": _pick(fields, "license_state", "status"), "number": _pick(fields, "license_number", "number"),
                       "address": _pick(fields, "address"), "ins": _pick(fields, "insurance"), "exp": _pick(fields, "expiration")}
    recs, r2 = _fetch_all(rid)
    sample = {k: v for k, v in (recs[0].items() if recs else []) if "owner" not in k.lower()}
    dropped = _drop_source(providers, "pgh_trade_licenses")
    n = 0
    for row in recs:
        ltype = str(row.get(fm.get("type") or "", "") or "")
        if license_filter and license_filter.lower() not in ltype.lower():
            continue
        name = (row.get(fm.get("name") or "", "") or "").strip()
        if not name:
            continue
        state = str(row.get(fm.get("state") or "", "") or "")
        creds = [{"type": "pgh_trade_license", "identifier": f"{ltype} {row.get(fm.get('number') or '', '')}".strip(),
                  "status": state or "unknown", "date": today(), "source_id": "pgh_trade_licenses",
                  "url": "https://data.wprdc.org/dataset/business-contractors-trades", "checked_by": "import"}]
        ins = row.get(fm.get("ins") or "", None) if fm.get("ins") else None
        if ins:
            creds.append({"type": "pgh_insurance_expiry", "identifier": "", "status": str(ins)[:10], "date": today(),
                          "source_id": "pgh_trade_licenses", "url": "", "checked_by": "import"})
        rec = {"name": name, "categories": ["electrician"] if "electric" in ltype.lower() else [ltype.lower()],
               "address": str(row.get(fm.get("address") or "", "") or ""), "source_id": "pgh_trade_licenses",
               "source_key": f"pgh:{row.get(fm.get('number') or '', '')}",
               "existence": {"basis": "City of Pittsburgh licensed trades dataset (CC0)", "date": today()},
               "service_area": None, "synthetic": False, "credentials": creds,
               "note": "License scope is the City of Pittsburgh; service area unknown until stated."}
        upsert(providers, rec); n += 1
    return {"ok": True, "imported": n, "replaced_previous": dropped, "resource_id": rid, "fields": fields, "field_map": fm,
            "sample_record": sample, "note": "License scope is the City of Pittsburgh only; a City license says nothing about suburbs."}


def import_radon_csv(providers: list[dict], path: str, list_date: str) -> dict:
    """PA DEP publishes certified tester/mitigator lists as monthly PDFs. Hand-transcribe the Allegheny rows into a CSV
    with columns: name,address,phone,role(tester|mitigator|lab),dep_id — then import. The list date is required."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    n = 0
    for row in csv.DictReader(io.StringIO(text)):
        role = (row.get("role") or "").strip().lower()
        rec = {"name": row["name"].strip(), "categories": ["radon"], "address": row.get("address", ""), "phone": row.get("phone", ""),
               "source_id": "padep_radon_lists", "source_key": f"dep:{row.get('dep_id', '')}",
               "existence": {"basis": f"PA DEP certified radon list dated {list_date} (hand-transcribed)", "date": list_date},
               "service_area": None, "synthetic": False,
               "credentials": [{"type": "padep_radon", "identifier": row.get("dep_id", ""), "status": role or "certified",
                                "date": list_date, "source_id": "padep_radon_lists",
                                "url": "https://www.pa.gov/agencies/dep/programs-and-services/radiation-protection/radon-division/radon-services-directory.html",
                                "checked_by": "import (manual transcription)"}]}
        upsert(providers, rec); n += 1
    return {"ok": True, "imported": n}


# ---------------------------------------------------------------- geocoding & distance
def geocode_provider(p: dict) -> bool:
    if p.get("lat") and p.get("lon") or not p.get("address"):
        return False
    r = http.fetch(http.q(COUNTY_GEOCODER, {"SingleLine": p["address"], "outSR": "4326", "maxLocations": "1",
                                            "outFields": "*", "f": "json"}), max_age_days=180)
    if r.ok and isinstance(r.data, dict) and r.data.get("candidates"):
        c = r.data["candidates"][0]
        if float(c.get("score", 0)) >= 85:
            p["lat"], p["lon"] = float(c["location"]["y"]), float(c["location"]["x"])
            p["geocode"] = {"score": c.get("score"), "date": today(), "source": "county_geocoder"}
            return True
    return False


def _haversine_mi(a, b) -> float:
    R = 3958.8
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- matching
def _suits(p: dict, category: str) -> bool:
    aliases = CATEGORY_ALIASES.get(category, [category])
    return any(any(a in c.lower() for a in aliases) for c in p.get("categories", []))


def _serves(p: dict, muni: Optional[str]) -> Optional[bool]:
    sa = p.get("service_area")
    if not sa:
        return None
    if not muni:
        return None
    m = muni.lower()
    for s in sa:
        s = s.lower()
        if s in ("allegheny county", "county-wide") or s in m or m in s:
            return True
        if "city of pittsburgh" in s and "pittsburgh" in m and "ward" in m:
            return True
    return False


def match(p: Profile, task: Task, providers: Optional[list[dict]] = None, *, max_results: int = 8) -> dict:
    providers = load() if providers is None else providers
    cat = task.provider_category
    if not cat:
        return {"category": "", "matches": [], "gap": "this task has no provider category", "checklist": hiring_checklist("")}
    muni = p.value("municipality")
    home = p.value("coordinates")
    home_xy = (home["lat"], home["lon"]) if isinstance(home, dict) else None
    rows = []
    for pr in providers:
        if pr.get("synthetic") and not p.synthetic:
            continue
        if not _suits(pr, cat):
            continue
        serves = _serves(pr, muni)
        creds = pr.get("credentials", [])
        relevant = [c for c in creds if _credential_relevant(c, cat, muni)]
        freshest = max((c.get("date") or "" for c in relevant), default=None)
        dist = _haversine_mi(home_xy, (pr["lat"], pr["lon"])) if home_xy and pr.get("lat") else None
        rows.append({"provider": pr, "serves": serves, "credentials": relevant, "freshest": freshest, "distance_mi": dist})

    def key(r):
        serves_rank = {True: 0, None: 1, False: 2}[r["serves"]]
        lic = 0 if any(c["type"] in LICENSE_TYPES for c in r["credentials"]) else (1 if r["credentials"] else 2)
        fresh = -(int((r["freshest"] or "0000-00-00").replace("-", "")) if r["freshest"] else 0)
        dist = r["distance_mi"] if r["distance_mi"] is not None else 1e9
        return (serves_rank, lic, fresh, dist, r["provider"]["name"].lower())
    rows.sort(key=key)
    rows = [r for r in rows if r["serves"] is not False][:max_results] or rows[:max_results]
    gap = ""
    if len(rows) < 3:
        gap = f"only {len(rows)} provider(s) on file for '{cat}' — inventory is thin; use the hiring checklist and add providers as you find them"
    return {"category": cat, "municipality": muni, "matches": rows, "gap": gap, "checklist": hiring_checklist(cat)}


def _is_city(muni: str) -> bool:
    m = muni.lower()
    return "pittsburgh" in m and ("ward" in m or m.strip() == "pittsburgh")


def _credential_relevant(c: dict, cat: str, muni: Optional[str]) -> bool:
    t = c["type"]
    if t == "hicpa":
        return True
    if t == "achd_master_plumber":
        return cat == "plumber"
    if t in ("pgh_trade_license", "pgh_insurance_expiry"):
        return cat == "electrician" or "electric" in (c.get("identifier") or "").lower()
    if t == "padep_radon":
        return cat == "radon"
    if t == "csia":
        return cat == "chimney"
    return True


def render_match(m: dict, p: Profile) -> str:
    out = [f"PROVIDERS FOR: {m['category'] or '—'}   (home municipality: {m.get('municipality') or 'unknown'})",
           "Ranked: task suitability → serves the address → verified credentials → freshness → distance. Unknown stays unknown.",
           "Registration/licensing is never proof of competence; workmanship evidence is not available from any permitted source."]
    if not m["matches"]:
        out.append("\n  no providers on file for this category" + (f" — {m['gap']}" if m["gap"] else ""))
    for i, r in enumerate(m["matches"], 1):
        pr = r["provider"]
        tag = "  [SYNTHETIC — demo only]" if pr.get("synthetic") else ""
        out.append(f"\n{i}. {pr['name']}{tag}")
        out.append(f"   listed as: {', '.join(pr.get('categories', []))}  (existence: {pr.get('existence', {}).get('basis', 'unknown')}, {pr.get('existence', {}).get('date', '?')})")
        serves = {True: "yes (stated service area)", False: "no (outside stated service area)", None: "unknown (no service area on file)"}[r["serves"]]
        out.append(f"   serves the address: {serves}")
        if r["credentials"]:
            for c in r["credentials"]:
                line = f"   credential: {wording(c)}" + (f" — {c['url']}" if c.get("url") else "")
                if c["type"] == "pgh_trade_license" and m.get("municipality") and not _is_city(m["municipality"]):
                    line += f"\n      note: this license covers work in the City of Pittsburgh; the house is in {m['municipality']}, where no municipal electrical license may exist — ask the municipality"
                out.append(line)
        else:
            out.append("   credential: none verified (unknown)")
        out.append("   insurance: " + next((wording(c) for c in r["credentials"] if c["type"] in ("pgh_insurance_expiry", "owner_saw_coi")), "unknown"))
        out.append("   workmanship: unknown (no permitted source)")
        out.append(f"   distance: {r['distance_mi']:.1f} mi" if r["distance_mi"] is not None else "   distance: unknown (address not geocoded)")
        if pr.get("phone"): out.append(f"   phone: {pr['phone']}")
        if pr.get("address"): out.append(f"   address: {pr['address']}")
        elif pr.get("base_city"): out.append(f"   based in: {pr['base_city']} (registry city; no address in source)")
        for cl in pr.get("claims", []):
            out.append(f"   provider claim (not checked): {cl}")
    if m["gap"]:
        out.append(f"\nGAP: {m['gap']}")
    out.append("\n" + m["checklist"])
    return "\n".join(out)


def hiring_checklist(cat: str) -> str:
    lines = ["HIRING CHECKLIST (what to verify yourself before signing)",
             "  □ PA HICPA registration: ask for the PA number; check at hicsearch.attorneygeneral.gov or 888-520-6680; the number must appear on the contract",
             "  □ Certificate of insurance naming you; HICPA requires $50k/$50k liability at registration but it can lapse",
             "  □ Written scope with exclusions, timeline, payment terms, and warranty",
             "  □ Who pulls permits and whether they are in the price"]
    extra = {"plumber": "  □ ACHD registered master plumber (HP number): eapps.alleghenycounty.us/Plumbing — required to pull a county plumbing permit",
             "electrician": "  □ City of Pittsburgh: trade license (City data); suburbs: ask the municipality — PA has no state electrician license",
             "radon": "  □ PA DEP certification (DEP ID) on the current monthly list; ask to see the DEP ID card",
             "chimney": "  □ CSIA certification (csia.org locator); which inspection level is quoted",
             "hvac": "  □ No PA or county HVAC license exists; HICPA registration + EPA 608 (technician states it; not verifiable by name)",
             "roofer": "  □ No PA roofing license; HICPA registration; manufacturer-certified installer status if a material warranty matters"}
    if cat in extra:
        lines.append(extra[cat])
    return "\n".join(lines)
