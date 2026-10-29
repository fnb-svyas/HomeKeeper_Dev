"""Reminders (Checkpoint 7): an explicitly defined, file-based method.

Method: the app writes an iCalendar (.ics) file for the next 12 months. The owner imports or subscribes
to it in any calendar app (Outlook, Google Calendar, Apple Calendar). Events are all-day, in the owner's
local calendar (no time-zone arithmetic), one VEVENT per occurrence, with a stable UID so re-importing
an updated file replaces events rather than duplicating them.

What this method does and does not do — stated plainly:
  * The .ics is a snapshot. It changes only when the owner re-exports after recording completions,
    corrections, snoozes or new findings. Nothing runs in the background.
  * Email, push and SMS delivery are deferred. The calendar app's own alerts are the notification.
  * Weather-triggered reminders (NWS alerts) are deferred (audit: keyless API available; automation would
    need a running process, which this prototype does not have).
  * Snoozed tasks move to their snooze date; done/dismissed/someone-else tasks produce no events;
    tasks that need an answer produce one "answer this" event rather than a recurring series.
Duplicate suppression: one event per (rule, date); merged rules already collapsed in the engine.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import pathlib

from . import HOUSES
from .evidence import Profile
from .rules import Task, evaluate, prioritize, _add_months, _parse_date

HORIZON_DAYS = 365


def _occurrences(t: Task, today: _dt.date, p: Profile) -> list[tuple[_dt.date, str]]:
    """Dates (within the horizon) on which this task should surface, with a short label."""
    rec = t.recurrence or {}
    typ = rec.get("type", "one_time")
    end = today + _dt.timedelta(days=HORIZON_DAYS)
    st = (getattr(p, "task_state", None) or {}).get(t.rule_id)
    if st and st.get("state") == "snoozed" and st.get("until"):
        d = _parse_date(st["until"])
        return [(d, "snoozed until")] if d and d <= end else []
    if t.status == "needs_info":
        return [(today, "answer the open question")]
    if t.status in ("verification", "finding"):
        return [(today, "verify" if t.status == "verification" else "documented finding — open")]
    if typ == "one_time":
        return [(today, "open until done")]
    if typ == "event":
        return []
    if typ == "fixed_date":
        mm, dd = map(int, rec["date"].split("-"))
        d = _dt.date(today.year, mm, dd)
        if d < today:
            d = _dt.date(today.year + 1, mm, dd)
        return [(d, "fixed date")] if d <= end else []
    if typ == "seasonal_window":
        sm, sd = map(int, rec["window"]["start"].split("-"))
        d = _dt.date(today.year, sm, sd)
        if d < today:
            d = _dt.date(today.year + 1, sm, sd)
        return [(d, f"window opens ({rec['window'].get('label', '')})")] if d <= end else []
    if typ in ("interval_since_completion", "equipment_interval"):
        months = int(rec.get("months", 12))
        last = None
        for c in (getattr(p, "completions", None) or []):
            if c.get("rule_id") == t.rule_id and (last is None or c["date"] > last):
                last = c["date"]
        ld = _parse_date(last)
        if ld is None:
            win = rec.get("window")
            first = today
            if win:
                sm, sd = map(int, win["start"].split("-"))
                ws = _dt.date(today.year, sm, sd)
                em, ed = map(int, win["end"].split("-"))
                we = _dt.date(today.year, em, ed)
                if we < ws: we = _dt.date(today.year + 1, em, ed)
                first = today if ws <= today <= we else (ws if ws > today else _dt.date(today.year + 1, sm, sd))
            label = "due now (no completion on record)" if first == today else "due (window opens)"
        else:
            first = _add_months(ld, months)
            label = "due"
            while first < today:
                first = _add_months(first, months)
                label = "overdue, next cycle"
        out, d = [], first
        while d <= end and len(out) < 24:
            out.append((d, label)); d = _add_months(d, months); label = "due"
        return out
    return []


def build_events(p: Profile, today: _dt.date | None = None) -> list[dict]:
    today = today or _dt.date.today()
    tasks = evaluate(p)
    live = [t for t in tasks if t.status in ("applies", "verification", "needs_info", "finding", "snoozed")]
    events, seen = [], set()
    for t in prioritize(tasks) + [t for t in live if t.status == "snoozed"]:
        for d, label in _occurrences(t, today, p):
            key = (t.rule_id, d)
            if key in seen:
                continue
            seen.add(key)
            uid = hashlib.sha1(f"{p.house_id}|{t.rule_id}|{d.isoformat()}".encode()).hexdigest()[:20] + "@homekeeper"
            events.append({"uid": uid, "date": d, "label": label, "task": t})
    events.sort(key=lambda e: (e["date"], e["task"].rule_id))
    return events


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545 line folding: lines at most 75 octets; continuation lines begin with a single space.
    Folds on character boundaries so multi-byte UTF-8 is never split."""
    out, cur, size = [], "", 0
    for ch in line:
        b = len(ch.encode("utf-8"))
        limit = 75 if not out else 74  # continuation lines carry a leading space
        if size + b > limit:
            out.append(cur); cur, size = ch, b
        else:
            cur += ch; size += b
    out.append(cur)
    return "\r\n ".join(out)


def to_ics(p: Profile, events: list[dict]) -> str:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//HomeKeeper prototype//EN", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
             _fold(f"X-WR-CALNAME:HomeKeeper — {p.value('matched_address') or p.address_input}"),
             _fold("X-WR-CALDESC:Snapshot exported by HomeKeeper; re-export after recording work. Not an emergency alert service.")]
    for e in events:
        t, d = e["task"], e["date"]
        desc = (f"{e['label']}\n{t.action}\nWhy this house: {t.why}\nDone when: {t.completion_criteria}\n"
                f"Rule {t.rule_id}; source: " + "; ".join(f"{s['source_id']}: {s['ref']}" for s in t.sources) +
                "\n(HomeKeeper snapshot — re-export after recording completions.)")
        lines += ["BEGIN:VEVENT", f"UID:{e['uid']}", f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
                  f"DTEND;VALUE=DATE:{(d + _dt.timedelta(days=1)).strftime('%Y%m%d')}",
                  _fold(f"SUMMARY:{_esc('[House] ' + t.title)}"), _fold(f"DESCRIPTION:{_esc(desc)}"),
                  _fold(f"CATEGORIES:{_esc(t.severity)},HomeKeeper"),
                  "BEGIN:VALARM", "ACTION:DISPLAY", _fold(f"DESCRIPTION:{_esc(t.title)}"), "TRIGGER:-P1D", "END:VALARM", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"  # every element of `lines` is already folded where it can exceed 75 octets


def export(p: Profile) -> pathlib.Path:
    d = HOUSES / p.house_id
    d.mkdir(parents=True, exist_ok=True)
    path = d / "reminders.ics"
    path.write_text(to_ics(p, build_events(p)), encoding="utf-8")
    return path


def render_upcoming(p: Profile, days: int = 90) -> str:
    today = _dt.date.today()
    evs = [e for e in build_events(p, today) if e["date"] <= today + _dt.timedelta(days=days)]
    out = [f"UPCOMING REMINDERS — next {days} days (from {today.isoformat()}); {len(evs)} event(s)",
           "This is a snapshot: it reflects the house record as of now and changes only when you record work and re-export."]
    cur = None
    for e in evs:
        if e["date"] != cur:
            cur = e["date"]; out.append(f"\n{cur.isoformat()}  {cur.strftime('%a')}")
        out.append(f"  • {e['task'].title}  [{e['task'].severity}; {e['label']}]")
    return "\n".join(out)


METHOD_STATEMENT = """REMINDER METHOD (explicit)
- What runs: nothing in the background. HomeKeeper writes houses/<id>/reminders.ics on request.
- How you get reminded: import or subscribe to that file in your calendar app; its alerts (one day before, all-day events) are the notification.
- What updates it: re-run 'reminders export' after recording completions, snoozes, corrections or findings. The file's event UIDs are stable, so re-importing replaces rather than duplicates.
- What is deferred: email, push and SMS delivery; weather-triggered reminders (NWS alerts); any scheduled process. A static hosted page cannot send notifications and HomeKeeper does not claim to.
- Not an emergency service: official alerts come from the National Weather Service and local authorities, not from this file."""
