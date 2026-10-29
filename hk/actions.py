"""Action tracking and house history (Checkpoint 5).

Profile additions (persisted in the house JSON):
  completions  - list of {id, rule_id, rule_version, component, date, notes, cost, contractor, documents[], recorded}
  task_state   - rule_id -> {"state": snoozed|does_not_apply|someone_else, "until", "reason", "date"}
  documents    - list of {id, kind, title, path_or_ref, component, rule_id, date, note}

Rules of the road (section 4D/4E of the brief):
  * A completion is the only thing that advances a recurring task's clock. Snoozing and "does not apply"
    never count as done; "already completed" is a completion with the date it actually happened.
  * Every dismissal captures a reason; when the reason implies the house record is wrong, the caller
    should correct the underlying field instead (the CLI offers that).
  * Nothing is deleted on dismissal; the task stays in the record with its state and reason so the
    30-day pilot can distinguish "irrelevant" from "done" from "someone else's".
"""
from __future__ import annotations

import datetime as _dt
from typing import Optional

from .evidence import Profile, today


def _ensure(p: Profile) -> None:
    for name, default in (("completions", []), ("task_state", {}), ("documents", [])):
        if getattr(p, name, None) is None:
            setattr(p, name, default)


def complete(p: Profile, rule_id: str, *, date: Optional[str] = None, notes: str = "", cost: Optional[float] = None,
             contractor: str = "", documents: Optional[list] = None, component: str = "", rule_version: int = 0) -> dict:
    _ensure(p)
    date = date or today()
    _dt.date.fromisoformat(date)  # validates
    rec = {"id": f"c-{len(p.completions)+1:03d}", "rule_id": rule_id, "rule_version": rule_version, "component": component,
           "date": date, "notes": notes, "cost": cost, "contractor": contractor, "documents": list(documents or []),
           "recorded": today()}
    p.completions.append(rec)
    p.task_state.pop(rule_id, None)  # a completion clears a snooze
    # a finding completion resolves the finding
    if rule_id.startswith("FINDING-"):
        fid = rule_id.split("FINDING-", 1)[1]
        for f in p.findings:
            if f["id"] == fid:
                f["status"] = "resolved"; f["resolved_on"] = date; f["resolution"] = notes
    # service date on the component's equipment record
    if component:
        e = p.installed(component)
        if e and (e.get("last_service_date") or "0000") < date:
            e["last_service_date"] = date
    p.log.append({"date": today(), "event": "completed", "rule_id": rule_id, "on": date, "cost": cost, "contractor": contractor})
    p.updated = today()
    return rec


def snooze(p: Profile, rule_id: str, until: str, reason: str = "") -> dict:
    _ensure(p)
    _dt.date.fromisoformat(until)
    st = {"state": "snoozed", "until": until, "reason": reason, "date": today()}
    p.task_state[rule_id] = st
    p.log.append({"date": today(), "event": "snoozed", "rule_id": rule_id, "until": until, "reason": reason})
    p.updated = today()
    return st


def does_not_apply(p: Profile, rule_id: str, reason: str) -> dict:
    _ensure(p)
    if not reason.strip():
        raise ValueError("a reason is required for 'does not apply' (it improves future recommendations)")
    st = {"state": "does_not_apply", "reason": reason, "date": today()}
    p.task_state[rule_id] = st
    p.log.append({"date": today(), "event": "does_not_apply", "rule_id": rule_id, "reason": reason})
    p.updated = today()
    return st


def reopen(p: Profile, rule_id: str, reason: str = "") -> None:
    _ensure(p)
    if p.task_state.pop(rule_id, None) is not None:
        p.log.append({"date": today(), "event": "reopened", "rule_id": rule_id, "reason": reason})
        p.updated = today()


def undo(p: Profile, rule_id: str) -> str:
    """Reverse the most recent action on a task: a completion recorded today, or a snooze/does-not-apply.
    Returns a short description of what was undone, or '' if nothing was undoable."""
    _ensure(p)
    st = p.task_state.get(rule_id)
    if st:
        p.task_state.pop(rule_id)
        p.log.append({"date": today(), "event": "undo", "rule_id": rule_id, "undid": st["state"]})
        p.updated = today()
        return "snooze" if st["state"] == "snoozed" else "does-not-apply"
    recs = [c for c in p.completions if c["rule_id"] == rule_id and c.get("recorded") == today()]
    if recs:
        rec = recs[-1]
        p.completions.remove(rec)
        if rule_id.startswith("FINDING-"):
            fid = rule_id.split("FINDING-", 1)[1]
            for f in p.findings:
                if f["id"] == fid and f.get("status") == "resolved":
                    f["status"] = "open"; f.pop("resolved_on", None); f.pop("resolution", None)
        if rec.get("component"):
            e = p.installed(rec["component"])
            if e and e.get("last_service_date") == rec["date"]:
                others = [c["date"] for c in p.completions if c.get("component") == rec["component"]]
                e["last_service_date"] = max(others) if others else None
        p.log.append({"date": today(), "event": "undo", "rule_id": rule_id, "undid": "completion", "completion": rec["id"]})
        p.updated = today()
        return "completion"
    return ""


def add_document(p: Profile, *, kind: str, title: str, ref: str, component: str = "", rule_id: str = "",
                 date: Optional[str] = None, note: str = "") -> dict:
    """Record a document reference (invoice, manual, warranty, photo, report). The file itself stays wherever
    the owner keeps it; only the reference is stored, so the house record never silently copies private files."""
    _ensure(p)
    d = {"id": f"d-{len(p.documents)+1:03d}", "kind": kind, "title": title, "ref": ref, "component": component,
         "rule_id": rule_id, "date": date or today(), "note": note, "recorded": today()}
    p.documents.append(d)
    if component:
        e = p.installed(component)
        if e and kind in ("manual", "warranty"):
            e.setdefault("warranty", {})[kind] = d["id"]
    p.log.append({"date": today(), "event": "document", "doc": d["id"], "kind": kind, "component": component})
    p.updated = today()
    return d


def last_completion(p: Profile, rule_id: str) -> Optional[dict]:
    _ensure(p)
    recs = [c for c in p.completions if c["rule_id"] == rule_id]
    return max(recs, key=lambda c: c["date"]) if recs else None


def state_of(p: Profile, rule_id: str) -> Optional[dict]:
    _ensure(p)
    st = p.task_state.get(rule_id)
    if not st:
        return None
    if st["state"] == "snoozed" and st.get("until") and st["until"] < today():
        return None  # snooze expired — task is open again
    return st


# ---------------------------------------------------------------- history views
def history(p: Profile) -> str:
    _ensure(p)
    out = [f"HOUSE HISTORY — {p.house_id}"]
    out.append("\nCOMPLETED WORK")
    spend = 0.0
    for c in sorted(p.completions, key=lambda c: c["date"]):
        cost = f"${c['cost']:,.0f}" if c.get("cost") is not None else "—"
        if c.get("cost"):
            spend += float(c["cost"])
        out.append(f"  {c['date']}  {c['rule_id']:<16} {cost:>8}  {c.get('contractor') or 'DIY':<22} {c.get('notes','')}")
        if c.get("documents"):
            out.append(f"             documents: {', '.join(c['documents'])}")
    out.append(f"  actual spending recorded: ${spend:,.0f}")
    out.append("\nEQUIPMENT")
    for e in p.equipment:
        out.append(f"  {e['id']} {e['component']:<14} {e.get('make','')} {e.get('model','')} installed {e.get('installed_year') or '?'}"
                   f"  last service {e.get('last_service_date') or '—'}  [{e['status']}]"
                   + (f"  replaced {e['replaced_on']}" if e.get('replaced_on') else ""))
    out.append("\nDOCUMENTS")
    for d in p.documents:
        out.append(f"  {d['id']} {d['kind']:<9} {d['title']:<40} {d['ref']}  ({d['date']}" + (f"; {d['component']}" if d['component'] else "") + ")")
    out.append("\nFINDINGS")
    for f in p.findings:
        out.append(f"  {f['id']} {f['component']:<12} {f['severity']:<7} {f['status']:<9} {f['description']}"
                   + (f"  resolved {f['resolved_on']}: {f.get('resolution','')}" if f.get('resolved_on') else ""))
    out.append("\nTASK STATES (snoozed / does not apply)")
    for rid, st in p.task_state.items():
        out.append(f"  {rid:<16} {st['state']}" + (f" until {st['until']}" if st.get('until') else "") + f"  — {st.get('reason','')}")
    out.append("\nCHANGE LOG (newest last)")
    for ev in p.log[-25:]:
        out.append("  " + ", ".join(f"{k}={v}" for k, v in ev.items() if v not in (None, "")))
    return "\n".join(out)


def export_json(p: Profile) -> dict:
    return p.to_dict()


def purge_private(p: Profile) -> dict:
    """Remove private material (documents, completions' notes/contractors, findings text, owner answers' notes)
    while keeping the public-record profile. Returns counts of what was removed."""
    _ensure(p)
    n = {"documents": len(p.documents), "completions": len(p.completions), "findings": len(p.findings),
         "log": len(p.log), "estimates": len(getattr(p, "estimates", []) or [])}
    p.documents, p.completions, p.findings, p.estimates, p.reserves, p.task_state = [], [], [], [], {}, {}
    p.log = [{"date": today(), "event": "private information purged"}]
    for name, d in list(p.fields.items()):
        if d.get("evidence_type") in ("owner_reported",):
            del p.fields[name]
    p.updated = today()
    return n
