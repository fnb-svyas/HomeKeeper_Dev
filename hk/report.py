"""Plain-text rendering of a profile and its provisional plan (CLI; the web UI comes in Checkpoint 8)."""
from __future__ import annotations

from .evidence import Profile, Field
from .rules import Task

EV_LABEL = {"public_record": "public record", "owner_reported": "owner", "professional_finding": "inspection",
            "manufacturer": "manufacturer", "regional_exposure": "regional", "inference": "inference", "unknown": "UNKNOWN"}


def _fmt(v):
    if isinstance(v, dict):
        return ", ".join(f"{k}={_fmt(x)}" for k, x in v.items() if x is not None and k not in ("note",))[:160]
    if isinstance(v, list):
        return f"{len(v)} item(s)"
    return str(v)


def _line(f: Field) -> str:
    val = "unknown" if f.is_unknown else _fmt(f.value) + (f" {f.units}" if f.units else "")
    tag = f"[{EV_LABEL.get(f.evidence_type, f.evidence_type)}; {f.verification_status}" + (f"; {f.source_id}" if f.source_id else "") + "]"
    s = f"  {f.name:<28} {val:<50} {tag}"
    if f.is_unknown and f.note:
        s += f"\n      -> {f.note}"
    if f.conflicts:
        s += f"\n      conflict kept: {[c.get('value') for c in f.conflicts]}"
    if f.history:
        s += f"\n      history: {[(h.get('value'), h.get('source_id')) for h in f.history]}"
    return s


def render_profile(p: Profile) -> str:
    out = []
    out.append(f"HOUSE RECORD  {p.house_id}   ({'SYNTHETIC DEMO DATA' if p.synthetic else p.mode})")
    out.append(f"Address entered: {p.address_input}")
    m = p.match
    if m.get("ambiguous") or m.get("chosen") is None:
        out.append(f"MATCH UNRESOLVED: {m.get('reason')}")
        for i, c in enumerate(m.get("candidates", [])):
            out.append(f"   [{i}] {c['address']}  score {c['score']:.0f}  parcel {c.get('parcel_id') or '-'}  ({c.get('addr_type')})")
        out.append("   -> re-run with --choose N to pick the right one")
    else:
        c = m["candidates"][m["chosen"]]
        out.append(f"Match: {c['address']}  (score {c['score']:.0f}, {c.get('addr_type')}; {m.get('reason')}; "
                   f"{'owner confirmed' if m.get('owner_confirmed') else 'not yet confirmed'})")
    out.append("\nPROPERTY FIELDS")
    for name in p.fields:
        out.append(_line(p.get(name)))
    if p.equipment:
        out.append("\nEQUIPMENT")
        for e in p.equipment:
            out.append(f"  {e['id']} {e['component']:<14} {e.get('make','')} {e.get('model','')}  installed {e.get('installed_year') or '?'}"
                       f"  manual: {e.get('manual_source_id') or 'none'}  [{e['status']}; {e['evidence_type']}]")
    if p.findings:
        out.append("\nDOCUMENTED FINDINGS")
        for f in p.findings:
            out.append(f"  {f['id']} {f['component']:<14} {f['severity']:<7} {f['description']}  ({f['source_doc']}; {f['status']})")
    if p.responsibilities:
        out.append("\nRESPONSIBILITIES: " + ", ".join(f"{k} -> {v}" for k, v in p.responsibilities.items()))
    out.append("\nREGIONAL EXPOSURE (describes the area, not this house)")
    for name in p.overlays:
        f = p.get(name)
        out.append(_line(f))
        if not f.is_unknown and f.limitations:
            out.append(f"      limits: {f.limitations}")
    return "\n".join(out)


def render_tasks(tasks: list[Task], *, show_all: bool = False, top: int | None = None) -> str:
    from .rules import prioritize, explain_priority
    out = ["\nPLAN (rules: author-reviewed against cited sources; not yet expert-validated)"]
    live = prioritize(tasks)
    if top:
        out.append(f"\nNEXT {top} ACTIONS")
        for i, t in enumerate(live[:top], 1):
            out.append(f"  {i}. {t.title}   [{t.severity}; {t.status}]")
            out.append(f"     why this house: {t.why}")
            out.append(f"     priority: {explain_priority(t)}")
    groups = {"finding": "DOCUMENTED FINDINGS", "applies": "APPLIES", "verification": "VERIFY FIRST",
              "needs_info": "NEEDS AN ANSWER", "snoozed": "SNOOZED (still open)", "dismissed": "MARKED DOES-NOT-APPLY (reason kept; not done)",
              "done": "DONE (one-time)", "someone_else": "SOMEONE ELSE'S RESPONSIBILITY",
              "excluded": "EXCLUDED BY CONFIRMED INFORMATION", "not_applicable": "NOT APPLICABLE (data gap)",
              "not_triggered": "NOT TRIGGERED"}
    for status, label in groups.items():
        items = [t for t in live if t.status == status] if status in ("finding", "applies", "verification", "needs_info") \
            else [t for t in tasks if t.status == status]
        if not items or (not show_all and status == "not_triggered"):
            continue
        out.append(f"\n{label}")
        for t in items:
            out.append(f"  {t.rule_id}  {t.title}  [{t.severity}]")
            if status in ("finding", "applies", "verification", "needs_info"):
                out.append(f"      why: {t.why}")
                out.append(f"      do:  {t.action}")
                if t.due:
                    out.append(f"      due: {t.due}")
                if t.refined_by:
                    out.append(f"      equipment: {t.refined_by}")
                if t.delay_consequence:
                    out.append(f"      if delayed: {t.delay_consequence}")
                extras = []
                if t.effort: extras.append(f"effort {t.effort}")
                if t.diy_pro: extras.append(t.diy_pro)
                c = t.cost or {}
                if c: extras.append("cost " + (c.get("basis", "unknown") if not c.get("range") else str(c["range"])))
                if t.provider_category: extras.append(f"provider: {t.provider_category}")
                out.append("      " + "; ".join(extras))
                if t.completion_criteria:
                    out.append(f"      done when: {t.completion_criteria}")
            if t.reason:
                out.append(f"      because: {t.reason}")
            ev = "; ".join(f"{e['field']}={_fmt(e['value']) if e['value'] is not None else 'unknown'} "
                           f"({EV_LABEL.get(e['evidence_type'], e['evidence_type'])})" for e in t.evidence)
            if ev:
                out.append(f"      evidence: {ev}")
            out.append("      source: " + " | ".join(f"{s['source_id']}: {s['ref']}" for s in t.sources))
    return "\n".join(out)


def render_questions(qs: list[dict]) -> str:
    if not qs:
        return "\nNo open questions."
    out = ["\nQUESTIONS THAT COULD CHANGE THE PLAN (answer with: answer <house> <field> <value>)"]
    for q in qs:
        unb = f"  (unblocks {', '.join(q['unblocks'])})" if q["unblocks"] else ""
        out.append(f"  {q['field']:<28} {q['question']}  [{q['answer']}]{unb}")
        if q["matters_because"]:
            out.append(f"      matters because: {q['matters_because']}")
    return "\n".join(out)
