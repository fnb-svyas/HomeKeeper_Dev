"""Connected reports (Checkpoint 4): before-you-buy, first-90-days, next three, 12-month calendar,
and the time-and-budget-constrained view. All are views over the same evaluated task list, so a
correction in the house record changes every report consistently.

None of these is a substitute for an inspection; the buy report says so in its first line.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

from .evidence import Profile, Field
from .rules import Task, prioritize, explain_priority
from . import budget as _budget

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _closing(p: Profile) -> Optional[_dt.date]:
    v = p.value("closing_date")
    try:
        return _dt.date.fromisoformat(str(v)[:10]) if v else None
    except ValueError:
        return None


def _fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{k}={v[k]}" for k in v if v[k] is not None and k != "note")[:120]
    return str(v)


# ---------------------------------------------------------------- before you buy
PROFILE_FIELDS_SHOWN = ["year_built", "style", "stories", "basement", "exterior_finish", "roof_type", "heating_cooling",
                        "condition_assessor", "grade_assessor", "living_area", "lot_area", "fireplaces", "municipality",
                        "heating_fuel", "heating_type", "roof_installed_year", "water_heater_installed_year",
                        "furnace_installed_year", "wiring_type", "plumbing_supply_material", "sump_pump_present"]


def before_you_buy(p: Profile, tasks: list[Task]) -> str:
    live = prioritize(tasks)
    out = ["BEFORE YOU BUY — what is known, what is not, and what to do before your deadlines",
           "This report is built from public records, regional data and whatever you have entered. It is not an "
           "inspection and not proof of the property's condition; the inspection report and the seller disclosure are "
           "the evidence that matters.", ""]
    out.append(f"House: {p.value('matched_address') or p.address_input}   stage: {p.value('stage') or 'unknown'}"
               + (f"   closing: {p.value('closing_date')}" if p.value("closing_date") else "   closing date: not entered"))

    out.append("\nWHAT IS KNOWN (with its source)")
    unknowns = []
    for name in PROFILE_FIELDS_SHOWN:
        f = p.get(name)
        if f.is_unknown:
            unknowns.append((name, f.note))
        else:
            out.append(f"  {name:<28} {_fmt(f.value)!s:<32} [{f.evidence_type}; {f.verification_status}]")
    out.append("\nWHAT IS NOT KNOWN YET")
    for name, note in unknowns:
        out.append(f"  {name:<28} unknown" + (f" — {note}" if note else ""))

    out.append("\nREGIONAL EXPOSURE (area, not this house)")
    for name in ("radon_zip_stats", "flood_zone", "undermined", "landslide_prone", "soil_map_unit"):
        f = p.get(name)
        out.append(f"  {name:<20} {('unknown — ' + f.note) if f.is_unknown else _fmt(f.value)}")

    out.append("\nBEFORE THE DEADLINES (transaction items)")
    deadline = [t for t in live if t.category == "deadline" or t.rule_id == "R-DISC-001"]
    for t in deadline:
        out.append(f"  • {t.title} — {t.action}")
    sewer = p.get("point_of_sale_sewer_rule")
    if not sewer.is_unknown and sewer.value.get("known"):
        v = sewer.value
        out.append(f"    Sewer certification ({v['name']}): {v['applies']}; performed by {v['performed_by']}; fee {v['fee']}; "
                   f"lead time {v['lead_time']}; valid {v['validity']}; camera {v['camera_inspection']}. Verify with the "
                   f"municipality (compiled {v['last_checked']}; {v['source_url']}).")

    out.append("\nFINDINGS THAT MAY WARRANT ADDITIONAL PROFESSIONAL ASSESSMENT")
    fnd = [t for t in live if t.status == "finding"]
    if fnd:
        for t in fnd:
            out.append(f"  • [{t.severity}] {t.title} — {t.action}")
    else:
        out.append("  none recorded yet — enter inspection findings with the 'finding' command")

    out.append("\nWHAT TO INSPECT OR ASK ABOUT (verification items)")
    for t in [t for t in live if t.status in ("verification", "needs_info")]:
        out.append(f"  • {t.title}: {t.action if t.status == 'verification' else t.reason}")

    b = _budget.build_budgets(p, tasks)
    out.append("\nKNOWN REPAIRS AND UNCERTAIN FIRST-YEAR EXPENSES")
    for i in b["repairs"]:
        out.append(f"  • {i['task']}: ${i['low']:,.0f}–${i['high']:,.0f} [{i['basis']}]")
    for i in b["replacements"]:
        out.append(f"  • {i['component']} replacement reserve: ${i['low']:,.0f}–${i['high']:,.0f} over {i['years']} yr [{i['basis']}]")
    for u in b["unknown"]:
        if u["budget"] in ("repairs", "replacements"):
            out.append(f"  • {u['task']}: cost unknown — {u['why']}")
    out.append("  Routine maintenance in year one: see the 12-month calendar and the routine budget.")

    out.append("\nRESPONSIBILITIES")
    if p.responsibilities:
        for k, v in p.responsibilities.items():
            out.append(f"  {k}: {v}")
    else:
        out.append("  homeowner for everything recorded; answer 'hoa_or_shared' or use 'responsibility' if anything is shared")

    out.append("\nWHAT COULD CHANGE THIS REPORT")
    for name, note in unknowns[:8]:
        out.append(f"  • {name} — once known: " + _why_matters(name))
    return "\n".join(out)


def _why_matters(name: str) -> str:
    from .questions import _why
    return _why(name) or "may add or remove tasks"


# ---------------------------------------------------------------- first 90 days / next three
def first_90_days(p: Profile, tasks: list[Task]) -> str:
    live = prioritize(tasks)
    start = _closing(p) or _dt.date.today()
    buckets = {"Week 1": [], "Weeks 2–4": [], "Days 31–60": [], "Days 61–90": [], "Later / recurring": []}
    for t in live:
        if t.status == "finding" or t.severity in ("safety", "deadline"):
            buckets["Week 1"].append(t)
        elif t.status == "verification" or t.severity == "health":
            buckets["Weeks 2–4"].append(t)
        elif t.severity == "damage" or t.status == "needs_info":
            buckets["Days 31–60"].append(t)
        elif t.category in ("replacement_planning",) or t.severity == "budget":
            buckets["Days 61–90"].append(t)
        else:
            buckets["Later / recurring"].append(t)
    out = [f"FIRST 90 DAYS OF OWNERSHIP (from {start.isoformat()}" + (" — closing date not entered; using today" if not _closing(p) else "") + ")",
           "Order within a week follows the explained priority (see 'priority:' lines)."]
    offsets = {"Week 1": (0, 7), "Weeks 2–4": (7, 30), "Days 31–60": (30, 60), "Days 61–90": (60, 90), "Later / recurring": (90, None)}
    for label, items in buckets.items():
        if not items:
            continue
        a, b = offsets[label]
        span = f"{(start + _dt.timedelta(days=a)).isoformat()} → {(start + _dt.timedelta(days=b)).isoformat()}" if b else f"after {(start + _dt.timedelta(days=a)).isoformat()}"
        out.append(f"\n{label}  ({span})")
        for t in items:
            out.append(f"  • {t.title}  [{t.severity}; {t.diy_pro}; effort {t.effort or '?'}]")
            out.append(f"      why: {t.why}")
            out.append(f"      priority: {explain_priority(t)}")
            if t.due:
                out.append(f"      due: {t.due}")
    return "\n".join(out)


def next_three(p: Profile, tasks: list[Task]) -> str:
    live = prioritize(tasks)[:3]
    out = ["NEXT THREE ACTIONS"]
    for i, t in enumerate(live, 1):
        out.append(f"{i}. {t.title}")
        out.append(f"   why it applies to this house: {t.why}")
        out.append(f"   what if you delay: {t.delay_consequence or 'not stated'}")
        out.append(f"   time/effort: {t.effort or 'unknown'}; {t.diy_pro}; cost basis: {(t.cost or {}).get('basis', 'unknown')}")
        out.append(f"   done when: {t.completion_criteria}")
        out.append(f"   keep afterwards: {t.retain or '—'}")
        out.append(f"   evidence: " + "; ".join(f"{e['field']}={_fmt(e['value']) if e['value'] is not None else 'unknown'} ({e['evidence_type']})" for e in t.evidence))
        out.append(f"   source: " + " | ".join(f"{s['source_id']}: {s['ref']}" for s in t.sources))
    return "\n".join(out)


# ---------------------------------------------------------------- 12-month calendar
def _months_for(t: Task, start: _dt.date) -> list[int]:
    """Month offsets (0..11 from start) in which the task should appear."""
    rec = t.recurrence or {}
    typ = rec.get("type", "one_time")
    cur = start.month
    offs = []
    if typ == "fixed_date":
        mm, dd = map(int, rec["date"].split("-"))
        off = (mm - cur) % 12
        if off == 0 and _dt.date.today().day > dd:
            return []  # this year's date has passed; next occurrence falls outside the 12-month window
        return [off]
    if typ == "seasonal_window" or (typ in ("interval_since_completion", "equipment_interval") and rec.get("window") and rec.get("months", 12) >= 12):
        win = rec["window"]
        sm, em = int(win["start"].split("-")[0]), int(win["end"].split("-")[0])
        m = sm
        while True:
            offs.append((m - cur) % 12)
            if m == em: break
            m = m % 12 + 1
        return sorted(set(offs))
    if typ in ("interval_since_completion", "equipment_interval"):
        step = int(rec.get("months", 12))
        if step <= 0: step = 12
        return list(range(0, 12, step)) if step < 12 else [0]
    if typ == "one_time":
        return [0]
    return []  # event-driven


def calendar(p: Profile, tasks: list[Task]) -> str:
    live = prioritize(tasks)
    start = _dt.date.today().replace(day=1)
    grid: dict[int, list[Task]] = {i: [] for i in range(12)}
    for t in live:
        for o in _months_for(t, start):
            grid[o].append(t)
    out = [f"12-MONTH CALENDAR (from {MONTHS[start.month-1]} {start.year}); recurring tasks reset from their actual completion dates once recorded"]
    for o in range(12):
        m = (start.month - 1 + o) % 12
        y = start.year + (start.month - 1 + o) // 12
        items = grid[o]
        out.append(f"\n{MONTHS[m]} {y}" + ("" if items else "  —"))
        for t in items:
            tag = {"finding": "FIX", "verification": "VERIFY", "needs_info": "ANSWER"}.get(t.status, "")
            out.append(f"  • {t.title}" + (f"  [{tag}]" if tag else "") + (f"  ({t.recurrence.get('type')}" + (f", every {t.recurrence['months']} mo)" if t.recurrence.get('months') else ")") if t.recurrence else ""))
    return "\n".join(out)


# ---------------------------------------------------------------- constrained view
def _effort_minutes(text: str) -> Optional[int]:
    if not text:
        return None
    s = text.lower()
    m = re.search(r"(\d+)\s*(?:–|-|to)?\s*(\d+)?\s*(minute|min|hour|hr)", s)
    if not m:
        return None
    hi = int(m.group(2) or m.group(1))
    return hi * (60 if m.group(3).startswith("h") else 1)


def constrained(p: Profile, tasks: list[Task], *, hours: float, dollars: float) -> str:
    live = prioritize(tasks)
    minutes_left, dollars_left = int(hours * 60), float(dollars)
    fits, skipped, urgent_out = [], [], []
    for t in live:
        if t.status == "needs_info":
            skipped.append((t, "answer the open question first")); continue
        est = _budget.estimate_for(p, t)
        cost_hi = est["high"] if est else (0.0 if (t.cost or {}).get("basis") == "none" or t.status == "verification" else None)
        mins = _effort_minutes(t.effort)
        pro = t.diy_pro in ("pro",)
        reason = None
        if pro:
            reason = "needs a professional visit (not a weekend DIY item)"
        elif mins is None:
            reason = "time unknown"
        elif cost_hi is None:
            reason = "cost unknown — price it first"
        elif mins > minutes_left:
            reason = f"needs ~{mins} min, {minutes_left} left"
        elif cost_hi > dollars_left:
            reason = f"up to ${cost_hi:,.0f}, ${dollars_left:,.0f} left"
        if reason is None:
            fits.append((t, mins, cost_hi)); minutes_left -= mins; dollars_left -= cost_hi
        else:
            (urgent_out if t.severity in ("safety", "health", "deadline") or t.status == "finding" else skipped).append((t, reason))
    out = [f"WITH {hours:g} HOURS AND ${dollars:,.0f}: what fits, in priority order"]
    for t, mins, c in fits:
        out.append(f"  ✓ {t.title}  (~{mins} min; ${c:,.0f})")
    out.append(f"  remaining: {minutes_left} min, ${dollars_left:,.0f}")
    if urgent_out:
        out.append("\nIMPORTANT ITEMS THAT DO NOT FIT THIS BUDGET — still need attention")
        for t, r in urgent_out:
            out.append(f"  ! {t.title}  [{t.severity}] — {r}")
    if skipped:
        out.append("\nDeferred (lower priority)")
        for t, r in skipped:
            out.append(f"  · {t.title} — {r}")
    return "\n".join(out)
