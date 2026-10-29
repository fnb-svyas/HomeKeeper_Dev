"""Data-driven rule engine. Rules live in data/rules.json (schema 0.2, see audit/rule_review.md).

Evaluation order per rule (section 5 of the brief):
  0. Responsibility: if the rule's component is assigned to another party -> "someone_else".
  1. Exclusions: any TRUE exclusion -> "excluded" (reason names the field and value).
  2. Required fields unknown -> per rule.when_unknown:
       ask -> "needs_info"; verify -> "verification" (uses rule.verification_task);
       apply -> evaluate anyway; skip -> "not_applicable" (reason shown).
  3. Triggers all TRUE (empty = always) -> "applies"; any unknown -> "needs_info".
  4. Equipment refinement: if the profile has installed equipment for rule.equipment_component whose
     manual_source_id matches a rule.variants entry, that variant's interval/action/source replaces the
     generic guidance (manufacturer instructions take precedence; both are shown).
  5. Recurrence -> a due label computed from completion/service dates where known.
Documented findings (inspection report) become tasks directly, separate from the rule base.
Tasks sharing a merge_key are merged (highest severity wins; sources are unioned).

Conflicting sources: a rule cites one primary source; where two free sources give different
intervals the rule states the range and names which source gives each bound (see water heater
rules). Manufacturer-specific instructions always refine generic guidance, never the reverse.
"""
from __future__ import annotations

import datetime as _dt
import json
import time
from dataclasses import dataclass, field, asdict
from functools import lru_cache

from . import DATA
from .evidence import Profile


@lru_cache(maxsize=1)
def load_rules() -> list[dict]:
    doc = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    return doc["rules"]


SEVERITY_ORDER = {"safety": 0, "health": 1, "deadline": 2, "damage": 3, "budget": 4, "comfort": 5, "info": 6}
EVIDENCE_STRENGTH = {"professional_finding": 0, "manufacturer": 0, "owner_reported": 1, "public_record": 2,
                     "regional_exposure": 3, "inference": 4, "unknown": 5}


@dataclass
class Task:
    rule_id: str
    title: str
    status: str                       # applies | verification | needs_info | excluded | someone_else | not_applicable | not_triggered | finding
    category: str
    severity: str
    why: str
    action: str
    component: str = ""
    evidence: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    reason: str = ""
    diy_pro: str = ""
    completion_criteria: str = ""
    safe_observation: str = ""
    pro_conditions: str = ""
    delay_consequence: str = ""
    effort: str = ""
    cost: dict = field(default_factory=dict)
    recurrence: dict = field(default_factory=dict)
    due: str = ""
    sources: list = field(default_factory=list)     # [{source_id, ref}]
    refined_by: str = ""                            # equipment-specific note, if a variant applied
    responsibility: str = "homeowner"
    retain: str = ""
    provider_category: str = ""
    merge_key: str = ""
    evidence_strength: int = 5
    seasonal_days_left: int | None = None

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------- values & conditions
def derive(values: dict, p: Profile | None = None) -> dict:
    """Derived fields: ages from installed years (profile fields first, then equipment records)."""
    year = int(time.strftime("%Y"))
    v = dict(values)
    pairs = [("roof", "roof_installed_year", "roof_age_years"),
             ("water_heater", "water_heater_installed_year", "water_heater_age_years"),
             ("furnace", "furnace_installed_year", "furnace_age_years"),
             ("ac", "ac_installed_year", "ac_age_years"),
             ("sump_pump", "sump_pump_installed_year", "sump_pump_age_years")]
    for comp, yr_field, age_field in pairs:
        if v.get(yr_field) is None and p is not None:
            e = p.installed(comp)
            if e and e.get("installed_year"):
                v[yr_field] = e["installed_year"]
        if v.get(yr_field) is not None and v.get(age_field) is None:
            v[age_field] = year - int(v[yr_field])
    if p is not None:
        if v.get("sump_pump_present") is None and p.installed("sump_pump"):
            v["sump_pump_present"] = True
        v["finding_components"] = sorted({f["component"] for f in p.findings if f.get("status") == "open"})
        v["open_safety_findings"] = sum(1 for f in p.findings if f.get("status") == "open" and f["severity"] == "safety")
    return v


def _lookup(values: dict, path: str):
    head, _, rest = path.partition(".")
    cur = values.get(head)
    while rest and isinstance(cur, dict):
        key, _, rest = rest.partition(".")
        cur = cur.get(key)
    return cur if not rest else None


def _test(cond: dict, values: dict):
    op, val = cond["op"], cond.get("value")
    cur = _lookup(values, cond["field"])
    if op == "unknown":
        return cur is None
    if op == "known":
        return cur is not None
    if cur is None:
        return None
    try:
        if op == "eq": return cur == val
        if op == "ne": return cur != val
        if op == "lt": return float(cur) < float(val)
        if op == "lte": return float(cur) <= float(val)
        if op == "gt": return float(cur) > float(val)
        if op == "gte": return float(cur) >= float(val)
        if op == "before_year": return int(cur) < int(val)
        if op == "in": return str(cur).lower() in [str(x).lower() for x in val]
        if op == "not_in": return str(cur).lower() not in [str(x).lower() for x in val]
        if op == "truthy": return bool(cur)
        if op == "falsy": return not bool(cur)
        if op == "contains": return str(val) in str(cur)
        if op == "icontains": return str(val).lower() in str(cur).lower()
        if op == "has": return (val in cur) if isinstance(cur, (list, tuple, set)) else False
    except (TypeError, ValueError):
        return None
    raise ValueError(f"unknown op {op}")


def profile_values(p: Profile) -> dict:
    vals = {}
    for store in (p.fields, p.overlays):
        for name, d in store.items():
            vals[name] = d.get("value")
    return derive(vals, p)


def _evidence_for(p: Profile, names: list[str]) -> list[dict]:
    out, seen = [], set()
    for n in names:
        base = n.split(".")[0]
        if base in seen or base in ("finding_components", "open_safety_findings"):
            continue
        seen.add(base)
        f = p.get(base)
        if f.is_unknown and base.endswith("_age_years"):
            continue
        out.append({"field": base, "value": None if f.is_unknown else f.value, "source_id": f.source_id,
                    "evidence_type": f.evidence_type, "status": f.verification_status, "source_ref": f.source_ref})
    return out


# ---------------------------------------------------------------- recurrence / due dates
def _parse_date(s):
    try:
        return _dt.date.fromisoformat(str(s)[:10])
    except (TypeError, ValueError):
        return None


def due_label(rec: dict, *, last_done=None, today: _dt.date | None = None) -> tuple[str, int | None]:
    """Human due label from a recurrence spec. Returns (label, days_until_window_end_or_None)."""
    today = today or _dt.date.today()
    t = rec.get("type", "one_time")
    if t == "one_time":
        return ("open until done", None)
    if t == "event":
        return (f"when: {rec.get('event', 'event occurs')}", None)
    if t == "fixed_date":
        mm, dd = map(int, rec["date"].split("-"))
        nxt = _dt.date(today.year, mm, dd)
        if nxt < today:
            nxt = _dt.date(today.year + 1, mm, dd)
        return (f"by {nxt.isoformat()}", (nxt - today).days)
    if t in ("interval_since_completion", "equipment_interval"):
        months = int(rec.get("months", 12))
        ld = _parse_date(last_done)
        if ld is None:
            label = "due now — no completion on record"
            win = rec.get("window")
            if win:
                lbl2, days = _season(win, today)
                return (f"{label}; best window {lbl2}", days)
            return (label, 0)
        nxt = _add_months(ld, months)
        if nxt <= today:
            return (f"overdue since {nxt.isoformat()} (last done {ld.isoformat()})", 0)
        return (f"next due {nxt.isoformat()} (last done {ld.isoformat()})", (nxt - today).days)
    if t == "seasonal_window":
        return _season(rec["window"], today)
    return ("", None)


def _add_months(d: _dt.date, months: int) -> _dt.date:
    y, m = d.year + (d.month - 1 + months) // 12, (d.month - 1 + months) % 12 + 1
    last = [31, 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return _dt.date(y, m, min(d.day, last))  # leap-year and short-month safe


def _season(win: dict, today: _dt.date) -> tuple[str, int]:
    sm, sd = map(int, win["start"].split("-"))
    em, ed = map(int, win["end"].split("-"))
    start = _dt.date(today.year, sm, sd)
    end = _dt.date(today.year, em, ed)
    if end < start:  # window wraps the year end
        end = _dt.date(today.year + 1, em, ed)
    if today > end:
        start, end = _dt.date(today.year + 1, sm, sd), _dt.date(today.year + 1, em, ed) if em >= sm else _dt.date(today.year + 2, em, ed)
    if start <= today <= end:
        return (f"in season now, window closes {end.isoformat()} ({win.get('label', '')})".replace(" ()", ""), (end - today).days)
    return (f"next window {start.isoformat()} to {end.isoformat()} ({win.get('label', '')})".replace(" ()", ""), (end - today).days)


# ---------------------------------------------------------------- evaluation
def _base_task(r: dict, p: Profile) -> Task:
    used = [c["field"] for c in r["trigger"]] + [c["field"] for c in r["exclusions"]] + r["required_fields"]
    return Task(rule_id=r["id"], title=r["title"], status="not_triggered", category=r["task_category"],
                severity=r["severity"], why=r["why"], action=r["action"], component=r["component"],
                evidence=_evidence_for(p, used), diy_pro=r["diy_pro"],
                completion_criteria=r["completion_criteria"], safe_observation=r.get("safe_observation", ""),
                pro_conditions=r.get("pro_conditions", ""), delay_consequence=r.get("delay_consequence", ""),
                effort=r.get("effort", ""), cost=dict(r.get("cost", {})), recurrence=dict(r.get("recurrence", {})),
                sources=[{"source_id": r["source_id"], "ref": r["source_ref"]}], retain=r.get("retain_evidence", ""),
                provider_category=r.get("provider_category", ""), merge_key=r.get("merge_key", ""))


def _refine_with_equipment(t: Task, r: dict, p: Profile) -> None:
    comp = r.get("equipment_component")
    if not comp:
        return
    e = p.installed(comp)
    if not e:
        return
    variant = (r.get("variants") or {}).get(e.get("manual_source_id") or "")
    if variant:
        if "months" in variant:
            t.recurrence = dict(t.recurrence, months=variant["months"])
        if "action" in variant:
            t.action = variant["action"]
        t.refined_by = (f"{e.get('make', '')} {e.get('model', '')}".strip() or comp) + " — " + variant.get("note", "manufacturer instructions")
        t.sources.append({"source_id": e["manual_source_id"], "ref": variant.get("source_ref", "manufacturer manual")})
        t.why = t.why + f" Refined by the installed equipment's own instructions ({e.get('make', '')} {e.get('model', '')})."
    elif e.get("manual_source_id"):
        t.refined_by = f"{comp}: manual {e['manual_source_id']} on file but no reviewed variant for this rule — generic guidance shown"
    else:
        t.refined_by = f"{comp} identified ({e.get('make', '')} {e.get('model', '')}) — no manual on file; generic guidance shown"


def _due(t: Task, r: dict, p: Profile) -> None:
    rec = t.recurrence
    if not rec:
        return
    last = None
    # 1. the most recent recorded completion of this rule
    for c in (getattr(p, "completions", None) or []):
        if c.get("rule_id") == t.rule_id and (last is None or c["date"] > last):
            last = c["date"]
    comp = r.get("equipment_component")
    if comp and last is None:
        e = p.installed(comp)
        if e:
            last = e.get("last_service_date")
            # a replacement counts as "done" for interval tasks that a new install satisfies
            if last is None and rec.get("reset_on_install") and e.get("installed_year"):
                last = f"{e['installed_year']}-01-01"
    t.due, t.seasonal_days_left = due_label(rec, last_done=last)


def evaluate(p: Profile) -> list[Task]:
    values = profile_values(p)
    tasks: list[Task] = []
    for r in load_rules():
        t = _base_task(r, p)
        # 0. responsibility
        party = p.responsibilities.get(r["component"]) or p.responsibilities.get(r.get("responsibility_component", ""))
        if party and r.get("responsibility_sensitive", True):
            t.status, t.responsibility = "someone_else", party
            t.reason = f"{r['component']} is {party}'s responsibility per the house record"
            tasks.append(t); continue
        # 1. exclusions
        done = False
        for c in r["exclusions"]:
            if _test(c, values) is True:
                t.status = "excluded"
                t.reason = f"excluded because {c['field']} = {_lookup(values, c['field'])!r} (confirmed information)"
                done = True; break
        if done:
            tasks.append(t); continue
        # 2. required fields
        missing = [f for f in r["required_fields"] if _lookup(values, f) is None]
        t.missing = missing
        if missing:
            mode = r.get("when_unknown", "skip")
            if mode == "ask":
                t.status, t.reason = "needs_info", f"needs {', '.join(missing)} to decide"
                tasks.append(t); continue
            if mode == "verify":
                t.status, t.reason = "verification", f"{', '.join(missing)} unknown — verify first"
                t.action = r.get("verification_task", t.action)
                t.diy_pro = "verification"
                tasks.append(t); continue
            if mode == "skip":
                if r.get("silent_when_unknown"):
                    t.status, t.reason = "not_triggered", f"{', '.join(missing)} not recorded (event/conditional rule)"
                else:
                    t.status, t.reason = "not_applicable", f"{', '.join(missing)} not available"
                tasks.append(t); continue
        # 3. triggers
        results = [_test(c, values) for c in r["trigger"]]
        if all(x is True for x in results):
            t.status = "applies"
            t.reason = "all trigger conditions met" if r["trigger"] else "applies to every home in the pilot"
        elif any(x is None for x in results):
            t.status, t.reason = "needs_info", "trigger depends on an unknown value"
        if t.status == "applies":
            _refine_with_equipment(t, r, p)
            _due(t, r, p)
        t.evidence_strength = min([EVIDENCE_STRENGTH.get(e["evidence_type"], 5) for e in t.evidence] or [5])
        tasks.append(t)
    tasks.extend(finding_tasks(p))
    tasks = merge(tasks)
    _apply_states(tasks, p)
    return tasks


def _apply_states(tasks: list[Task], p: Profile) -> None:
    """Overlay owner actions: snoozes (until a date), 'does not apply' (with reason), and one-time completions."""
    states = getattr(p, "task_state", None) or {}
    done_once = {c["rule_id"] for c in (getattr(p, "completions", None) or [])}
    for t in tasks:
        if t.status not in ("applies", "verification", "needs_info", "finding"):
            continue
        st = states.get(t.rule_id)
        if st and st["state"] == "snoozed" and st.get("until", "") >= time.strftime("%Y-%m-%d"):
            t.status, t.reason = "snoozed", f"snoozed until {st['until']}" + (f" — {st['reason']}" if st.get("reason") else "")
        elif st and st["state"] == "does_not_apply":
            t.status, t.reason = "dismissed", f"owner: does not apply — {st['reason']} (not counted as done)"
        elif t.rule_id in done_once and (t.recurrence or {}).get("type") in ("one_time", "event") and t.status != "finding":
            t.status, t.reason = "done", "completed (one-time task)"
        elif t.status == "finding":
            pass


PROVIDER_BY_COMPONENT = {"electrical": "electrician", "roof": "roofer", "gutters_downspouts": "gutter", "plumbing": "plumber",
                         "water_heater": "plumber", "sewer_lateral": "plumber", "heating": "hvac", "ac": "hvac",
                         "chimney": "chimney", "radon": "radon", "foundation": "engineer", "structure": "engineer",
                         "basement": "waterproofing", "grading": "landscaper", "site": "engineer"}


def finding_tasks(p: Profile) -> list[Task]:
    out = []
    sev_map = {"safety": "safety", "major": "damage", "minor": "comfort", "info": "info"}
    for f in p.findings:
        if f.get("status") != "open":
            continue
        resp = p.responsibilities.get(f["component"])
        t = Task(rule_id=f"FINDING-{f['id']}", title=f"Documented finding: {f['description'][:70]}",
                 status="someone_else" if resp else "finding", category="documented_defect",
                 severity=sev_map.get(f["severity"], "damage"),
                 why=f"Documented in {f['source_doc']}" + (f" on {f['observed_date']}" if f.get("observed_date") else "") + ".",
                 action=f.get("recommendation") or "Obtain a professional assessment and quotes; record the outcome.",
                 component=f["component"],
                 evidence=[{"field": f"finding {f['id']}", "value": f["description"], "source_id": f["source_doc"],
                            "evidence_type": "professional_finding", "status": "documented", "source_ref": f.get("location", "")}],
                 reason=(f"{f['component']} is {resp}'s responsibility" if resp else f"{f['severity']} finding, open"),
                 diy_pro="pro" if f["severity"] in ("safety", "major") else "diy_or_pro",
                 completion_criteria="Repair or assessment documented in the house record and the finding marked resolved.",
                 delay_consequence={"safety": "a documented hazard remains in place",
                                    "major": "documented damage can progress; repair scope and cost tend to grow",
                                    "minor": "small defect may worsen; low urgency",
                                    "info": "none stated by the inspector"}.get(f["severity"], ""),
                 effort="depends on scope — get quotes", retain="invoice, before/after photos, any warranty",
                 recurrence={"type": "one_time"}, due="open until resolved",
                 provider_category=PROVIDER_BY_COMPONENT.get(f["component"], ""),
                 sources=[{"source_id": f["source_doc"], "ref": f.get("location", "")}],
                 responsibility=resp or "homeowner", evidence_strength=0, merge_key="")
        out.append(t)
    return out


def merge(tasks: list[Task]) -> list[Task]:
    """Merge tasks sharing a merge_key (only live statuses merge). Highest severity wins; sources union."""
    kept: dict[str, Task] = {}
    out: list[Task] = []
    for t in tasks:
        key = t.merge_key if t.status in ("applies", "verification", "needs_info") else ""
        if not key:
            out.append(t); continue
        if key not in kept:
            kept[key] = t; out.append(t); continue
        a = kept[key]
        if SEVERITY_ORDER.get(t.severity, 9) < SEVERITY_ORDER.get(a.severity, 9):
            a.severity = t.severity
        a.sources += [s for s in t.sources if s not in a.sources]
        a.why += f" Also: {t.why}"
        a.reason += f"; merged with {t.rule_id}"
    return out


def prioritize(tasks: list[Task]) -> list[Task]:
    """Explainable ordering: documented defects and safety first, then deadlines, then by evidence strength,
    then by how soon a seasonal window closes, then budget planning. Never a numeric score."""
    live = [t for t in tasks if t.status in ("finding", "applies", "verification", "needs_info")]
    # recurring tasks whose next due date is in the future drop below everything due now
    status_order = {"finding": 0, "applies": 1, "verification": 2, "needs_info": 3}

    def cls(t: Task) -> int:
        # explainable tiers: documented safety defects, then safety rules, then documented damage,
        # then health, deadlines, damage prevention, budget planning, comfort, info
        if t.status == "finding" and t.severity == "safety": return 0
        if t.status == "finding" and t.severity == "damage": return 1   # documented, progressing, strong evidence
        if t.severity == "safety": return 2
        if t.status == "finding": return 3
        return {"health": 4, "deadline": 5, "damage": 6, "budget": 7, "comfort": 8, "info": 9}.get(t.severity, 10)

    def key(t: Task):
        days = t.seasonal_days_left if t.seasonal_days_left is not None else 10_000
        not_yet_due = 1 if t.due.startswith("next due") else 0
        return (not_yet_due, cls(t), status_order[t.status], t.evidence_strength, days, t.rule_id)
    return sorted(live, key=key)


def explain_priority(t: Task) -> str:
    bits = [("documented defect — " if t.status == "finding" else "") + f"severity: {t.severity}"]
    bits.append({"finding": "documented defect", "applies": "rule applies", "verification": "needs verification first",
                 "needs_info": "needs an answer"}.get(t.status, t.status))
    bits.append({0: "strong evidence", 1: "owner-reported", 2: "public record", 3: "regional exposure", 4: "inference",
                 5: "unknown"}.get(t.evidence_strength, ""))
    if t.due.startswith("due now"):
        bits.append("no completion on record")
    elif t.due.startswith("overdue"):
        bits.append("overdue")
    if t.seasonal_days_left is not None and "window" in t.due:
        bits.append(f"window closes in {t.seasonal_days_left} days")
    return "; ".join(b for b in bits if b)
