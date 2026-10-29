"""HomeKeeper Ownership Score (0-100): a transparent planning indicator for Browse Homes.

Deterministic and rule-based (no model calls). Every weight, band and point value comes from
data/score_config.json, which is a set of product assumptions, not validated measures.

  price       - asking price per sq ft against recent valid sales of similar homes nearby
  maintenance - recurring upkeep load from size, exterior, stories, lot, basement, insurance exposure,
                and whether an association handles the exterior
  major       - supported exposure to substantial one-time projects (documented findings, roof age
                where established, the assessor's poor ratings, items that need professional assessment)

Each expense is assigned to exactly one component (see ASSIGNMENT). A component that lacks its
essential inputs is "unavailable"; the overall score is then withheld rather than reweighted.
Unknown optional inputs take a stated assumption that is never the best case. Evidence completeness
is reported separately and never enters the score.
"""
from __future__ import annotations

import datetime as _dt
import json
from functools import lru_cache
from typing import Optional

from . import DATA, buyer
from .evidence import Profile

ASSIGNMENT = [
    ("Asking price vs. comparable sales", "Price position"),
    ("Size, exterior walls, stories, lot", "Ongoing maintenance"),
    ("Basement moisture control (dehumidifying, gutters, grading)", "Ongoing maintenance"),
    ("Flood insurance and mine-subsidence insurance premiums", "Ongoing maintenance"),
    ("Association handling of exterior upkeep", "Ongoing maintenance"),
    ("Roof replacement (only when its age or condition is established)", "Major-work exposure"),
    ("Documented defects from a report on this house", "Major-work exposure"),
    ("Waterproofing or drainage projects; slope and retaining walls", "Major-work exposure"),
    ("Sewer-line repair after a sale-time test; unfinished permitted work", "Major-work exposure"),
]


@lru_cache(maxsize=1)
def config() -> dict:
    return json.loads((DATA / "score_config.json").read_text(encoding="utf-8"))


def parse_price(raw) -> Optional[int]:
    """'$345,000', '345000', '345k' or '1.2m' -> int dollars; '' -> None; nonsense -> ValueError."""
    s = str(raw or "").strip().lower().replace("$", "").replace(",", "").replace(" ", "")
    if not s:
        return None
    mult = 1000 if s.endswith("k") else 1_000_000 if s.endswith("m") else 1
    v = float(s.rstrip("km")) * mult
    if not (1000 <= v <= 50_000_000):
        raise ValueError("out of range")
    return int(round(v))


def set_inputs(p: Profile, *, asking_price=None, hoa_exterior: str = "unknown", clear_price: bool = False) -> None:
    """Record the buyer's own inputs (labelled as theirs) and keep their history; the caller saves."""
    from .evidence import Field
    if clear_price:
        if not p.get("asking_price").is_unknown:
            p.set(Field(name="asking_price", note="cleared by you"), reason="asking price cleared")
    elif asking_price is not None and asking_price != p.value("asking_price"):
        p.correct("asking_price", asking_price, source_id="user", reason="asking price entered in Browse Homes", units="USD")
    if hoa_exterior in ("yes", "no") and hoa_exterior != p.value("hoa_exterior"):
        p.correct("hoa_exterior", hoa_exterior, source_id="user", reason="entered in Browse Homes")
    elif hoa_exterior == "unknown" and not p.get("hoa_exterior").is_unknown:
        p.set(Field(name="hoa_exterior", note="set back to not known"), reason="association answer cleared")


def _round_to(x: float, step: int) -> int:
    import math
    return int(step * math.floor(x / step + 0.5)) if step > 1 else int(math.floor(x + 0.5))


def label_for(score: int) -> dict:
    for b in config()["labels"]:
        if score >= b["min"]:
            return b
    return config()["labels"][-1]


def _d(text, points, component, kind="fact"):
    """A driver: points > 0 hurts, points < 0 helps, 0 with text helps (a favourable fact)."""
    return {"text": text, "points": points, "component": component, "kind": kind}


# ---------------------------------------------------------------- price
def price_component(p: Profile) -> dict:
    cfg = config()["price"]
    ask = p.get("asking_price")
    bench = p.get("price_benchmark")
    area = buyer._pv(p, "living_area")
    need = []
    if ask.is_unknown:
        need.append("an asking price (enter it below)")
    if not area:
        need.append("the home's living area in the public record")
    if bench.is_unknown:
        need.append("enough recent comparable sales (" + (bench.note or "benchmark not retrieved") + ")")
    out = {"key": "price", "name": "Price position", "available": False, "score": None, "drivers": [],
           "needed": need, "inputs": {}, "assumptions": []}
    if not ask.is_unknown:
        out["inputs"]["asking_price"] = {"value": ask.value, "source": "You entered this", "date": (ask.retrieved_date or "")[:10]}
    if not bench.is_unknown:
        out["inputs"]["benchmark"] = bench.value
        out["benchmark_field"] = bench
    if need:
        out["status_text"] = "Price assessment unavailable"
        return out
    ppsf = float(ask.value) / float(area)
    med = float(bench.value["median_ppsf"])
    ratio = ppsf / med
    band = next(b for b in cfg["bands"] if b["max_ratio"] is None or ratio <= b["max_ratio"])
    pct = abs(round((ratio - 1) * 100))
    out.update(available=True, score=int(band["points"]), ratio=round(ratio, 3), ask_ppsf=round(ppsf))
    out["drivers"].append(_d(band["text"].format(pct=pct), 0 if band["points"] >= 70 else 100 - band["points"], "price"))
    if bench.value.get("window_months", 0) > cfg["window_months"]:
        out["assumptions"].append(f"Too few sales in {cfg['window_months']} months, so the benchmark reaches back {bench.value['window_months']} months; older prices may lag the market.")
    if bench.value.get("scope") == "municipality":
        out["assumptions"].append("Too few sales in the assessor neighbourhood, so the benchmark uses the whole municipality.")
    return out


# ---------------------------------------------------------------- maintenance
def maintenance_component(p: Profile) -> dict:
    cfg = config()["maintenance"]
    area = buyer._pv(p, "living_area")
    ext = buyer._pv(p, "exterior_finish")
    out = {"key": "maintenance", "name": "Ongoing maintenance", "available": False, "score": None, "drivers": [],
           "needed": [], "inputs": {}, "assumptions": []}
    if not area:
        out["needed"].append("the home's living area")
    if not ext:
        out["needed"].append("the exterior wall material")
    if out["needed"]:
        out["status_text"] = "Maintenance assessment unavailable"
        return out
    drivers, ded = [], 0

    band = next(b for b in cfg["size_sqft"] if b["max"] is None or area <= b["max"])
    if band["text"]:
        drivers.append(_d(band["text"].format(sqft=f"{int(area):,}"), band["points"], "maintenance"))
    ded += band["points"]

    e = str(ext).lower()
    cls = next((c for c in ("low", "high", "medium") if any(m in e for m in cfg["exterior"][c]["match"])), None)
    pts = cfg["exterior"][cls]["points"] if cls else cfg["exterior"]["other_points"]
    txt = cfg["exterior"][cls]["text"] if cls else "{ext} exterior walls: upkeep needs uncertain, counted as moderate."
    if txt:
        drivers.append(_d(txt.format(ext=buyer._title(ext)), pts, "maintenance"))
    ded += pts

    st = buyer._pv(p, "stories")
    if st is None:
        ded += cfg["stories"]["unknown_points"]
        out["assumptions"].append(f"Number of stories not recorded: counted as two or more (−{cfg['stories']['unknown_points']}).")
    elif float(st) >= 2:
        ded += cfg["stories"]["two_or_more_points"]
        drivers.append(_d(cfg["stories"]["text"], cfg["stories"]["two_or_more_points"], "maintenance"))

    lot = buyer._pv(p, "lot_area")
    if lot is None:
        ded += cfg["lot_unknown_points"]
        out["assumptions"].append(f"Lot size not recorded: counted as a modest lot (−{cfg['lot_unknown_points']}).")
    else:
        lb = next(b for b in cfg["lot_sqft"] if b["max"] is None or lot <= b["max"])
        ded += lb["points"]
        if lb["text"]:
            drivers.append(_d(lb["text"].format(lot=f"{int(lot):,}"), lb["points"], "maintenance"))

    bs = buyer._pv(p, "basement")
    if bs is None:
        ded += cfg["basement_unknown_points"]
        out["assumptions"].append(f"Basement not recorded: counted as having one (−{cfg['basement_unknown_points']}).")
    elif str(bs).lower() in ("full", "part"):
        ded += cfg["basement_points"]
        drivers.append(_d(cfg["basement_text"].format(bs=str(bs).lower()), cfg["basement_points"], "maintenance"))

    fz = buyer._public(p, "flood_zone")
    if fz.is_unknown or not isinstance(fz.value, dict) or fz.value.get("sfha") is None:
        ded += cfg["flood_unknown_points"]
        out["assumptions"].append(f"Flood zone not retrieved: a partial flood-insurance allowance is counted (−{cfg['flood_unknown_points']}).")
    elif fz.value.get("sfha"):
        ded += cfg["flood_sfha_points"]
        drivers.append(_d(cfg["flood_sfha_text"], cfg["flood_sfha_points"], "maintenance"))

    if buyer._pv(p, "undermined") is True:
        ded += cfg["undermined_points"]
        drivers.append(_d(cfg["undermined_text"], cfg["undermined_points"], "maintenance"))

    hoa = p.get("hoa_exterior")
    if not hoa.is_unknown and hoa.value == "yes":
        ded -= cfg["shared_exterior_bonus"]
        drivers.append(_d(cfg["shared_exterior_text"].format(what="you said an association handles it"), -cfg["shared_exterior_bonus"], "maintenance"))
        out["inputs"]["hoa_exterior"] = {"value": "yes", "source": "You entered this"}
    elif not hoa.is_unknown:
        out["inputs"]["hoa_exterior"] = {"value": hoa.value, "source": "You entered this"}

    out.update(available=True, score=max(0, min(100, 100 - ded)), drivers=drivers)
    return out


# ---------------------------------------------------------------- major work
def _roof_status(p: Profile) -> dict:
    cfg = config()["major"]["roof"]
    year = _dt.date.today().year
    ry = p.get("roof_installed_year")
    rt = str(buyer._pv(p, "roof_type") or "").lower()
    if not ry.is_unknown:
        age = year - int(ry.value)
        src = "you entered" if ry.source_id in ("owner", "user") else "public record"
        long_life = rt and "shingle" not in rt
        if age < cfg["recent_max_age"] or long_life:
            return {"state": "documented_recent", "points": cfg["recent_documented_points"], "age": age,
                    "text": cfg["recent_documented_text"].format(basis=f"A recorded {ry.value} roof installation ({src})")}
        if age >= cfg["past_window_age"]:
            return {"state": "planning", "points": cfg["past_window_points"], "age": age, "text": cfg["past_window_text"].format(age=age)}
        return {"state": "planning", "points": cfg["planning_points"], "age": age, "text": cfg["planning_text"].format(age=age)}
    for r in reversed(buyer._roof_permits(p)):
        d = str(r.get("issue_date") or "")[:4]
        if buyer._is_closed(r) and d.isdigit() and year - int(d) < cfg["recent_max_age"]:
            return {"state": "documented_recent", "points": cfg["recent_documented_points"], "age": year - int(d),
                    "text": cfg["recent_documented_text"].format(basis=f"A finaled {d} city roof permit")}
    return {"state": "unknown", "points": cfg["unknown_points"], "age": None, "text": cfg["unknown_text"]}


def major_component(p: Profile) -> dict:
    cfg = config()["major"]
    out = {"key": "major", "name": "Major-work exposure", "available": False, "score": None, "drivers": [],
           "needed": [], "inputs": {}, "assumptions": [], "documented": 0}
    if buyer._public(p, "parcel_id").is_unknown or (buyer._pv(p, "year_built") is None and buyer._pv(p, "condition_assessor") is None
                                                      and buyer._pv(p, "roof_type") is None):
        out["needed"].append("a matched county parcel record")
        out["status_text"] = "Major-work assessment unavailable"
        return out
    drivers, ded = [], 0
    items = buyer.major_work(p)
    documented_components = set()
    for it in items:
        if it["status"] == "documented":
            comp = it["key"]
            f = next((x for x in p.findings if "finding-" + x["id"] == comp), None)
            what = (f["component"] + " findings") if f else "work items"
            if f and f["component"] in documented_components:
                continue  # one documented deduction per component: the same repair isn't counted twice
            if f:
                documented_components.add(f["component"])
            ded += cfg["documented_points"]; out["documented"] += 1
            drivers.append(_d(cfg["documented_text"].format(what=what.replace("_", " ")), cfg["documented_points"], "major", "documented"))
        elif it["key"] == "condition":
            ded += cfg["assessor_poor_points"]
            drivers.append(_d(cfg["assessor_poor_text"].format(cond=buyer._title(buyer._pv(p, "condition_assessor"))), cfg["assessor_poor_points"], "major", "assess"))
        elif it["key"] == "roof":
            continue  # handled by the roof status below
        else:
            kind = "permit" if it["key"].startswith("permit-") else it["key"]
            pts = cfg["assess_points"].get(kind, 0)
            ded += pts
            drivers.append(_d(cfg["assess_text"][kind], pts, "major", "assess"))
    roof = _roof_status(p)
    out["roof"] = roof
    if "roof" in documented_components:
        out["assumptions"].append("A documented roof finding already counts; the roof's age isn't counted again.")
    else:
        ded += roof["points"]
        drivers.append(_d(roof["text"], roof["points"], "major", "planning" if roof["state"] == "planning" else
                          ("unknown" if roof["state"] == "unknown" else "fact")))
    out.update(available=True, score=max(0, min(100, 100 - ded)), drivers=drivers)
    return out


# ---------------------------------------------------------------- completeness (never used in the score)
def completeness(p: Profile, roof: Optional[dict]) -> dict:
    cfg = config()["completeness"]
    known, missing = [], []
    labels = {"asking_price": "asking price", "price_benchmark": "comparable-sales benchmark", "living_area": "living area",
              "exterior_finish": "exterior walls", "stories": "stories", "lot_area": "lot size", "basement": "basement",
              "flood_zone": "flood zone", "roof_age": "roof age", "condition_assessor": "assessor condition rating",
              "year_built": "year built"}
    for name in cfg["inputs"]:
        if name == "roof_age":
            ok = bool(roof) and roof.get("state") != "unknown"
        elif name in ("asking_price", "price_benchmark"):
            ok = not p.get(name).is_unknown
        else:
            ok = buyer._pv(p, name) is not None
        (known if ok else missing).append(labels[name])
    frac = len(known) / len(cfg["inputs"])
    level = next(l["label"] for l in cfg["levels"] if frac >= l["min"])
    return {"known": known, "missing": missing, "n_known": len(known), "n": len(cfg["inputs"]), "level": level}


# ---------------------------------------------------------------- overall
def compute(p: Profile) -> dict:
    c = config()
    comps = [price_component(p), maintenance_component(p), major_component(p)]
    by = {x["key"]: x for x in comps}
    w = c["weights"]
    avail = all(x["available"] for x in comps)
    overall = raw = None
    if avail:
        raw = sum(w[k] * by[k]["score"] for k in w)
        overall = _round_to(raw, c["overall_display_rounding"])
    drivers = [d for x in comps for d in x["drivers"]]
    hurting = sorted([d for d in drivers if d["points"] > 0], key=lambda d: (-d["points"], d["text"]))
    helping = [d for d in drivers if d["points"] <= 0]
    needed = [f"{x['name']}: {n}" for x in comps for n in x["needed"]]
    major_items = buyer.major_work(p)
    return {"overall": overall, "raw": round(raw, 1) if raw is not None else None,
            "label": label_for(overall) if overall is not None else None,
            "components": comps, "weights": w, "hurting": hurting, "helping": helping, "needed": needed,
            "assumptions": [a for x in comps for a in x["assumptions"]],
            "completeness": completeness(p, by["major"].get("roof")),
            "documented_major": sum(1 for m in major_items if m["status"] == "documented"),
            "open_major": len(major_items), "config_version": c["version"], "review_status": c["review_status"]}
