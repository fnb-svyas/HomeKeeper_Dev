"""Cost estimates and the three budgets (section 4F of the brief).

Estimates are stored on the profile (`profile.estimates`) and are never invented:
  basis = user_quote | published_reference | planning_assumption
Every estimate carries range, scope, exclusions, geographic basis, source and date.
Tasks without an estimate show "unknown" and are listed, not summed.

Three budgets are kept separate and de-duplicated:
  routine      - recurring preventive tasks (annualised from recurrence)
  repairs      - documented findings and documented_defect tasks
  replacements - replacement-planning tasks, as reserve scenarios (period chosen by the user)
A component with both a repair and a replacement scenario is flagged as a possible overlap.
"""
from __future__ import annotations

import time
from typing import Optional

from .evidence import Profile, today
from .rules import Task

BASES = ("user_quote", "published_reference", "planning_assumption")


def add_estimate(p: Profile, *, applies_to: str, low: float, high: float, basis: str, scope: str,
                 exclusions: str = "", geo: str = "Allegheny County, PA", source: str = "", date: Optional[str] = None,
                 note: str = "") -> dict:
    assert basis in BASES, basis
    if not hasattr(p, "estimates") or p.estimates is None:
        p.estimates = []
    est = {"id": f"est-{len(p.estimates)+1:03d}", "applies_to": applies_to, "low": float(low), "high": float(high),
           "basis": basis, "scope": scope, "exclusions": exclusions, "geo": geo, "source": source or basis,
           "date": date or today(), "note": note, "recorded": today()}
    p.estimates.append(est)
    p.log.append({"date": today(), "event": "estimate added", "estimate": est["id"], "applies_to": applies_to, "basis": basis})
    p.updated = today()
    return est


def estimate_for(p: Profile, task: Task) -> Optional[dict]:
    ests = getattr(p, "estimates", None) or []
    for key in (task.rule_id, task.component):
        for e in reversed(ests):
            if e["applies_to"] == key:
                return e
    return None


def set_reserve(p: Profile, *, component: str, years: int, low: float, high: float, basis: str, source: str = "",
                note: str = "") -> dict:
    """Reserve scenario for a future replacement: the owner chooses the planning period and the range."""
    assert basis in BASES
    if not hasattr(p, "reserves") or p.reserves is None:
        p.reserves = {}
    r = {"component": component, "years": int(years), "low": float(low), "high": float(high), "basis": basis,
         "source": source or basis, "date": today(), "note": note}
    p.reserves[component] = r
    p.log.append({"date": today(), "event": "reserve scenario", "component": component, "years": years})
    p.updated = today()
    return r


def _per_year(rec: dict) -> Optional[float]:
    t = rec.get("type")
    if t in ("interval_since_completion", "equipment_interval"):
        m = rec.get("months")
        return 12.0 / float(m) if m else None
    if t in ("fixed_date", "seasonal_window"):
        return 1.0
    return None  # one_time / event: not routine


def _fmt_money(x: float) -> str:
    return f"${x:,.0f}"


def build_budgets(p: Profile, tasks: list[Task]) -> dict:
    live = [t for t in tasks if t.status in ("applies", "finding", "verification", "needs_info")]
    routine, repairs, replacements, unknown_cost = [], [], [], []
    components_with_repairs = {t.component for t in live if t.status == "finding" or t.category == "documented_defect"}

    for t in live:
        est = estimate_for(p, t)
        per_year = _per_year(t.recurrence)
        if t.status == "finding" or t.category == "documented_defect":
            components_with_repairs.add(t.component)
            if est:
                repairs.append({"task": t.title, "rule_id": t.rule_id, "component": t.component, "low": est["low"],
                                "high": est["high"], "basis": est["basis"], "scope": est["scope"], "exclusions": est["exclusions"],
                                "geo": est["geo"], "source": est["source"], "date": est["date"]})
            else:
                unknown_cost.append({"budget": "repairs", "task": t.title, "rule_id": t.rule_id,
                                     "why": "no quote on file — get quotes (job brief available in Checkpoint 5)"})
        elif t.category == "replacement_planning" and t.status == "applies":
            res = (getattr(p, "reserves", None) or {}).get(t.component)
            if res:
                months = res["years"] * 12
                replacements.append({"task": t.title, "rule_id": t.rule_id, "component": t.component, "years": res["years"],
                                     "low": res["low"], "high": res["high"], "basis": res["basis"], "source": res["source"],
                                     "date": res["date"], "monthly_low": res["low"] / months, "monthly_high": res["high"] / months,
                                     "overlap": t.component in components_with_repairs})
            else:
                unknown_cost.append({"budget": "replacements", "task": t.title, "rule_id": t.rule_id,
                                     "why": "no reserve scenario — choose a planning period and a cost range (reserve command)"})
        elif per_year is not None and t.status == "applies":
            cost = (t.cost or {})
            if est:
                routine.append({"task": t.title, "rule_id": t.rule_id, "per_year": per_year, "low": est["low"] * per_year,
                                "high": est["high"] * per_year, "basis": est["basis"], "scope": est["scope"],
                                "source": est["source"], "date": est["date"], "diy_pro": t.diy_pro})
            elif cost.get("basis") == "none":
                routine.append({"task": t.title, "rule_id": t.rule_id, "per_year": per_year, "low": 0.0, "high": 0.0,
                                "basis": "none", "scope": "no purchase required (your time only)", "source": "rule", "date": today(),
                                "diy_pro": t.diy_pro})
            else:
                unknown_cost.append({"budget": "routine", "task": t.title, "rule_id": t.rule_id,
                                     "why": cost.get("note") or "no price source; enter your quote"})
    # overlap check: a repair and a replacement on the same component
    for r in replacements:
        if r["overlap"]:
            r["overlap_note"] = "a documented repair exists for this component — if it is replaced, the repair is moot; do not count both"

    def total(items):
        return (sum(i["low"] for i in items), sum(i["high"] for i in items))

    return {"as_of": today(), "routine": routine, "repairs": repairs, "replacements": replacements,
            "unknown": unknown_cost,
            "totals": {"routine_per_year": total(routine), "repairs": total(repairs),
                       "replacement_reserve_per_month": (sum(r["monthly_low"] for r in replacements),
                                                         sum(r["monthly_high"] for r in replacements))},
            "note": ("Totals cover only items with a recorded quote, published reference, or planning assumption; "
                     "items under 'unknown' are not included and are the next things to price.")}


def render_budgets(b: dict) -> str:
    out = [f"BUDGETS (as of {b['as_of']})", b["note"], ""]
    out.append("1. ROUTINE MAINTENANCE (annualised)")
    for i in b["routine"]:
        rng = "your time only" if i["basis"] == "none" else f"{_fmt_money(i['low'])}–{_fmt_money(i['high'])}/yr [{i['basis']}; {i['source']} {i['date']}]"
        out.append(f"   {i['task'][:60]:<60} ×{i['per_year']:.1f}/yr  {rng}")
    lo, hi = b["totals"]["routine_per_year"]
    out.append(f"   total of priced items: {_fmt_money(lo)}–{_fmt_money(hi)} per year")
    out.append("\n2. KNOWN REPAIRS (documented findings)")
    for i in b["repairs"]:
        out.append(f"   {i['task'][:60]:<60} {_fmt_money(i['low'])}–{_fmt_money(i['high'])} [{i['basis']}; {i['source']} {i['date']}; {i['geo']}]")
        out.append(f"      scope: {i['scope']}" + (f"; excludes: {i['exclusions']}" if i["exclusions"] else ""))
    lo, hi = b["totals"]["repairs"]
    out.append(f"   total of priced items: {_fmt_money(lo)}–{_fmt_money(hi)}")
    out.append("\n3. FUTURE REPLACEMENTS (reserve scenarios; average service life is not a failure date)")
    for i in b["replacements"]:
        out.append(f"   {i['component']:<14} {_fmt_money(i['low'])}–{_fmt_money(i['high'])} over {i['years']} yr "
                   f"→ set aside {_fmt_money(i['monthly_low'])}–{_fmt_money(i['monthly_high'])}/month [{i['basis']}; {i['source']} {i['date']}]")
        if i.get("overlap_note"):
            out.append(f"      overlap: {i['overlap_note']}")
    lo, hi = b["totals"]["replacement_reserve_per_month"]
    out.append(f"   total monthly reserve of priced scenarios: {_fmt_money(lo)}–{_fmt_money(hi)}")
    if b["unknown"]:
        out.append("\nUNPRICED (not in any total)")
        for u in b["unknown"]:
            out.append(f"   [{u['budget']}] {u['task'][:60]:<60} — {u['why']}")
    return "\n".join(out)
