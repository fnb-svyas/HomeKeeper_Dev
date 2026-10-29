"""HTML rendering for the local web app (stdlib only). One CSS string, small template helpers.

Visual identity: a house record and field guide. Document serif for the record, system sans for
controls. Provenance tags on every fact; unknowns drawn as visible gaps; severity carried by a thin
rule, not by tinted cards. No scores anywhere.
"""
from __future__ import annotations

import datetime as _dt
import html
from typing import Iterable

from . import VERSION, actions, budget, providers, questions, reminders, reports, rules
from .evidence import Profile, Field

CSS = """
:root{--paper:#F4F4F1;--ink:#243039;--ink-2:#4F5B64;--brick:#8E3A2B;--verdigris:#2E6E66;--mortar:#D8D5CE;--chalk:#FFFFFF;--slate:#5B6B78;--mustard:#8A6A1F}
@media(prefers-color-scheme:dark){:root{--paper:#1C2227;--ink:#E8E6E1;--ink-2:#B8B4AC;--brick:#D6705E;--verdigris:#6FB3A8;--mortar:#3A434A;--chalk:#232B31;--slate:#9AA9B4;--mustard:#C9A24A}}
*{box-sizing:border-box}html{font-size:17px}
body{margin:0;background:var(--paper);color:var(--ink);font-family:"Palatino Linotype","Iowan Old Style","Book Antiqua",Palatino,Georgia,serif;line-height:1.5}
a{color:inherit}
.ui,button,input,select,textarea,.nav,.tag,.meta,.btn,table{font-family:"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif}
header.top{display:flex;align-items:baseline;gap:1.25rem;padding:1rem 16px;border-bottom:1px solid var(--mortar);flex-wrap:wrap}
header.top .brand{font-size:1.15rem;letter-spacing:.01em}
header.top .brand b{font-weight:600}
.nav{display:flex;flex-wrap:wrap;gap:.2rem 1rem;min-width:0}.nav a{font-size:.9rem;color:var(--ink-2);text-decoration:none}
.nav a[aria-current]{color:var(--ink);border-bottom:2px solid var(--brick)}
main{max-width:72rem;margin:0 auto;padding:1.25rem 16px 4rem}
.cols{display:grid;grid-template-columns:minmax(0,1fr);gap:2rem}
@media(min-width:900px){.cols{grid-template-columns:17rem minmax(0,1fr)}}
.rail{font-size:.92rem;color:var(--ink-2)}
.rail h2{font-size:1.4rem;color:var(--ink);margin:.2rem 0 .4rem;font-weight:500;line-height:1.2}
.rail dl{margin:0}.rail dt{color:var(--ink-2);font-size:.8rem;margin-top:.6rem}.rail dd{margin:0;color:var(--ink)}
h1{font-size:2rem;font-weight:500;line-height:1.15;margin:.2rem 0 1rem;max-width:30ch}
h2{font-size:1.35rem;font-weight:500;margin:2rem 0 .6rem}
h3{font-size:1.05rem;font-weight:600;margin:1.2rem 0 .4rem;font-family:"Segoe UI",system-ui,sans-serif}
p,li{max-width:70ch}
.next{list-style:none;counter-reset:n;padding:0;margin:0 0 1rem}
.next>li{counter-increment:n;display:grid;grid-template-columns:3rem minmax(0,1fr);gap:.5rem 1rem;padding:1.1rem 0;border-top:1px solid var(--mortar)}
.next>li:first-child{border-top:2px solid var(--ink)}
.next>li::before{content:counter(n);font-size:2.6rem;line-height:1;color:var(--brick);font-weight:500;grid-row:span 3}
.next .title{font-size:1.3rem;line-height:1.25;margin:0}
.next .why{margin:.25rem 0 0;color:var(--ink-2)}
.next .meta{font-size:.82rem;color:var(--ink-2);margin:.3rem 0 0}
.task{border-left:3px solid var(--slate);padding:.6rem 0 .6rem 1rem;margin:.6rem 0}
.task.safety{border-color:var(--brick)}.task.health{border-color:var(--mustard)}.task.deadline{border-color:var(--mustard)}
.task.done,.task.someone_else,.task.excluded,.task.dismissed,.task.snoozed{border-color:var(--mortar);color:var(--ink-2)}
.task .t{margin:0;font-size:1.08rem}
.task .meta{font-size:.82rem;color:var(--ink-2);margin:.15rem 0}
.task .row{margin:.3rem 0 0}.task p.row{margin:.35rem 0 0}details.act summary{color:var(--ink)}
details{margin:.3rem 0}summary{cursor:pointer;font-family:"Segoe UI",system-ui,sans-serif;font-size:.85rem;color:var(--ink-2)}
details[open] summary{color:var(--ink)}
.ev{font-size:.9rem;margin:.4rem 0 0;padding-left:1rem;border-left:1px dotted var(--mortar)}
.tag{display:inline-block;font-size:.72rem;padding:.05rem .4rem;border:1px solid var(--mortar);border-radius:2px;color:var(--ink-2);vertical-align:middle;margin-left:.3rem;white-space:nowrap}
.tag.rec{border-color:var(--slate)}.tag.own{border-color:var(--verdigris);color:var(--verdigris)}.tag.pro{border-color:var(--verdigris);color:var(--verdigris)}
.tag.reg{border-color:var(--mustard);color:var(--mustard)}.tag.unk{border-style:dotted}
.unknown{border-bottom:2px dotted var(--brick);color:var(--ink-2)}
.fields{width:100%;border-collapse:collapse;font-size:.92rem}
.fields td{padding:.35rem .5rem .35rem 0;border-top:1px solid var(--mortar);vertical-align:top}
.fields td:first-child{color:var(--ink-2);width:14rem;font-family:"Segoe UI",system-ui,sans-serif;font-size:.82rem}
.fields td{overflow-wrap:anywhere}
@media(max-width:600px){.fields td:first-child{width:7.5rem}.next>li{grid-template-columns:2.2rem minmax(0,1fr)}.next>li::before{font-size:2rem}html{font-size:16px}}
input,select{max-width:100%;min-width:0}.row>*{min-width:0}form.inline{display:inline-block;max-width:100%}
.limits{font-size:.8rem;color:var(--ink-2);max-width:70ch}
form.inline{display:inline}
.btn,button{font-size:.85rem;padding:.3rem .7rem;border:1px solid var(--ink);background:var(--chalk);color:var(--ink);border-radius:3px;cursor:pointer}
.btn.quiet,button.quiet{border-color:var(--mortar);color:var(--ink-2)}
.btn.primary{background:var(--ink);color:var(--paper)}
button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--verdigris);outline-offset:2px}
input,select,textarea{font-size:.9rem;padding:.3rem .4rem;border:1px solid var(--mortar);border-radius:3px;background:var(--chalk);color:var(--ink);max-width:100%}
.row{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin:.4rem 0}
.q{padding:.6rem 0;border-top:1px solid var(--mortar)}
.q label{display:block;font-size:1rem}
.q .because{font-size:.82rem;color:var(--ink-2)}
pre.doc{white-space:pre-wrap;font-family:inherit;font-size:.95rem;line-height:1.45;background:var(--chalk);padding:1rem;border:1px solid var(--mortar);overflow-x:auto}
.tbl{overflow-x:auto;max-width:100%}table.b{border-collapse:collapse;width:100%;font-size:.9rem}table.b td{overflow-wrap:anywhere}table.b td,table.b th{text-align:left;padding:.4rem .5rem;border-top:1px solid var(--mortar);vertical-align:top}
table.b th{font-weight:600;color:var(--ink-2);font-size:.8rem}
.notice{border:1px solid var(--mortar);padding:.6rem .9rem;font-size:.9rem;background:var(--chalk);max-width:70ch}
.notice.synthetic{border-color:var(--brick)}
.gap{color:var(--ink-2);font-style:italic}
.cal .m{margin:1rem 0}.cal .m h3{margin:.2rem 0}
footer{padding:2rem 16px;border-top:1px solid var(--mortar);font-size:.8rem;color:var(--ink-2);max-width:72rem;margin:0 auto}
@media(prefers-reduced-motion:no-preference){details[open] .ev{animation:reveal .18s ease-out}}
@keyframes reveal{from{opacity:0;transform:translateY(-2px)}to{opacity:1;transform:none}}
"""

EV_TAG = {"public_record": ("public record", "rec"), "owner_reported": ("owner", "own"), "professional_finding": ("inspection", "pro"),
          "manufacturer": ("manufacturer", "pro"), "regional_exposure": ("regional", "reg"), "inference": ("inference", "unk"),
          "unknown": ("unknown", "unk")}


def e(s) -> str:
    return html.escape(str(s if s is not None else ""), quote=True)


def tag(f: Field) -> str:
    label, cls = EV_TAG.get(f.evidence_type, (f.evidence_type, "unk"))
    status = "" if f.is_unknown else f" · {f.verification_status.replace('_', ' ')}"
    return f'<span class="tag {cls}">{e(label)}{e(status)}</span>'


def fmt(v) -> str:
    if isinstance(v, dict):
        return ", ".join(f"{k} {v[k]}" for k in v if v[k] is not None and k != "note")[:140]
    if isinstance(v, list):
        return f"{len(v)} item(s)"
    return str(v)


def page(title: str, body: str, *, nav: Iterable[tuple[str, str, bool]] = (), snapshot: bool = False) -> str:
    cur_attr = ' aria-current="page"'
    navs = "".join(f'<a href="{e(h)}"{cur_attr if cur else ""}>{e(t)}</a>' for h, t, cur in nav)
    note = ('<div class="notice synthetic" style="margin:1rem 16px 0">This is a read-only snapshot built from a synthetic sample house. '
            'Buttons and forms are simulated and do nothing here; the local app records them.</div>') if snapshot else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><style>{CSS}</style></head><body>
<header class="top"><a class="brand" href="/" style="text-decoration:none"><b>HomeKeeper</b></a><nav class="nav">{navs}</nav></header>{note}
<main>{body}</main>
<footer>HomeKeeper prototype {e(VERSION)} · Allegheny County pilot · Not an inspection and not proof of a property's condition. Rules are author-reviewed against cited sources, not yet expert-validated.</footer>
</body></html>"""


# ---------------------------------------------------------------- pieces
def rail(p: Profile) -> str:
    addr = p.value("matched_address") or p.address_input
    rows = [("Built", p.value("year_built")), ("Style", p.value("style")), ("Basement", p.value("basement")),
            ("Exterior", p.value("exterior_finish")), ("Roof", p.value("roof_type")), ("Heating", p.value("heating_cooling")),
            ("Municipality", p.value("municipality")), ("Parcel", p.value("parcel_id")), ("Stage", p.value("stage")),
            ("Closing", p.value("closing_date"))]
    dl = "".join(f"<dt>{e(k)}</dt><dd>{e(v) if v is not None else '<span class=unknown>unknown</span>'}</dd>" for k, v in rows)
    syn = '<p class="notice synthetic">Synthetic demo house</p>' if p.synthetic else ""
    return f'<aside class="rail"><h2>{e(addr)}</h2>{syn}<dl>{dl}</dl></aside>'


def task_block(p: Profile, t: rules.Task, *, actions_on: bool = True) -> str:
    sev = e(t.severity)
    status = e(t.status)
    ev = "".join(f'<div>{e(x["field"])}: {e(fmt(x["value"])) if x["value"] is not None else "<span class=unknown>unknown</span>"} '
                 f'<span class="tag {EV_TAG.get(x["evidence_type"], ("", "unk"))[1]}">{e(EV_TAG.get(x["evidence_type"], (x["evidence_type"], ""))[0])}</span></div>'
                 for x in t.evidence)
    src = "<br>".join(f"{e(s['source_id'])}: {e(s['ref'])}" for s in t.sources)
    who = {"diy": "you can do this", "pro": "needs a professional", "diy_or_pro": "you or a professional",
           "verification": "a quick check", "planning": "planning only"}.get(t.diy_pro, t.diy_pro)
    cost = {"none": "no cost", "unknown": "cost not known yet", "planning_assumption": "small cost", "published_reference": "see note"}.get((t.cost or {}).get("basis", ""), "")
    due = t.due.split(";")[0].replace("due now — no completion on record", "Due now").replace("open until done", "Open").replace("open until resolved", "Open")
    meta = " · ".join(x for x in (due, f"about {t.effort}" if t.effort and t.effort[0].isdigit() else t.effort, who, cost) if x)
    if t.refined_by and "—" in t.refined_by:
        meta += " · interval from your unit's manual"
    act = ""
    if actions_on and t.status in ("applies", "verification", "needs_info", "finding"):
        hid = e(p.house_id); rid = e(t.rule_id)
        act = f"""<details class="act"><summary>Done, snooze, doesn't apply, find a provider…</summary><div class="row">
<form class="inline" method="post" action="/house/{hid}/done"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="next" value="tasks">
<input type="date" name="date" value="{_dt.date.today().isoformat()}" aria-label="date done"> <input name="notes" placeholder="notes" size="18"> <input name="cost" placeholder="cost $" size="7" inputmode="decimal"> <input name="contractor" placeholder="contractor" size="14"> <button class="primary">Done</button></form>
<form class="inline" method="post" action="/house/{hid}/snooze"><input type="hidden" name="task" value="{rid}"><input type="date" name="until" aria-label="snooze until" required> <input name="reason" placeholder="reason" size="12"> <button class="quiet">Snooze</button></form>
<form class="inline" method="post" action="/house/{hid}/dismiss"><input type="hidden" name="task" value="{rid}"><input name="reason" placeholder="why it does not apply" size="20" required> <button class="quiet">Does not apply</button></form>
<a class="btn quiet" href="/house/{hid}/providers/{rid}">Find a provider</a> <a class="btn quiet" href="/house/{hid}/brief/{rid}">Write a job brief</a>
</div></details>"""
    elif actions_on and t.status in ("snoozed", "dismissed"):
        act = f'<form class="inline" method="post" action="/house/{e(p.house_id)}/reopen"><input type="hidden" name="task" value="{e(t.rule_id)}"><button class="quiet">Reopen</button></form>'
    show_status = status not in ("applies", "finding")
    return f"""<div class="task {sev} {status}"><p class="t">{e(t.title)} <span class="tag">{sev}</span>{f'<span class="tag">{status.replace("_", " ")}</span>' if show_status else ''}</p>
<p class="meta">{e(meta)}</p>
<details><summary>Why this house, and the source</summary><div class="ev"><p>{e(t.why)}</p><p><b>Do:</b> {e(t.action)}</p>
{f'<p><b>If delayed:</b> {e(t.delay_consequence)}</p>' if t.delay_consequence else ''}
{f'<p><b>Done when:</b> {e(t.completion_criteria)}</p>' if t.completion_criteria else ''}
{f'<p><b>Because:</b> {e(t.reason)}</p>' if t.reason else ''}
<p><b>Evidence:</b></p>{ev or '<div class=gap>none</div>'}<p><b>Source:</b> {src}</p></div></details>{act}</div>"""


def _priority_line(t: rules.Task) -> str:
    why = {"finding": "documented defect", "applies": "rule applies", "verification": "needs verification first",
           "needs_info": "needs an answer"}.get(t.status, t.status)
    ev = {0: "strong evidence", 1: "owner-reported", 2: "public record", 3: "regional exposure", 4: "inference", 5: "evidence unknown"}.get(t.evidence_strength, "")
    bits = [f"{t.severity}", why, ev]
    if t.due:
        bits.append(t.due.split(";")[0])
    return " · ".join(b for b in bits if b)


def _label(name: str) -> str:
    return name.replace("_", " ")


# ---------------------------------------------------------------- pages
def houses_page(ids: list[str]) -> str:
    items = "".join(f'<li><a href="/house/{e(i)}">{e(i)}</a></li>' for i in ids) or '<li class="gap">No houses yet.</li>'
    body = f"""<h1>Your houses</h1><ul>{items}</ul>
<h2>Add a house</h2>
<form method="post" action="/build" class="row"><input name="address" size="48" placeholder="123 Main St, Pittsburgh, PA 15228" required> <button class="primary">Look up this address</button></form>
<p class="limits">Looks up the parcel in Allegheny County records and the regional overlays (radon history, flood zone, mining, landslide, soil). Takes a few seconds; nothing is sent anywhere except those public data services.</p>
<h2>Synthetic demo houses</h2>
<form method="post" action="/sample" class="row"><select name="name"><option value="complete">complete — 1928 brick colonial, Mt. Lebanon</option><option value="missing">missing — sparse assessor record, City of Pittsburgh</option><option value="ambiguous">ambiguous — two equal matches</option></select> <button>Create</button></form>
<p class="limits">Demo houses are invented. Their records say so on every page.</p>"""
    return page("HomeKeeper", body, nav=[("/", "Houses", True)])


def nav_for(p: Profile, cur: str):
    h = f"/house/{p.house_id}"
    cur = {"plan": "tasks", "record": "house", "budget": "money", "reports": "today"}.get(cur, cur)
    return [(h, "Today", cur == "today"), (f"{h}/tasks", "Tasks", cur == "tasks"), (f"{h}/house", "House", cur == "house"),
            (f"{h}/money", "Money", cur == "money"), (f"{h}/history", "History", cur == "history")]


def record_page(p: Profile, msg: str = "") -> str:
    m = p.match
    match_html = ""
    if m.get("ambiguous") or m.get("chosen") is None:
        cands = "".join(f'<li>{e(c["address"])} — score {c["score"]:.0f}, parcel {e(c.get("parcel_id") or "—")} '
                        f'<form class="inline" method="post" action="/house/{e(p.house_id)}/choose"><input type="hidden" name="choose" value="{i}"><button>This one</button></form></li>'
                        for i, c in enumerate(m.get("candidates", [])))
        match_html = f'<div class="notice"><b>Address match unresolved:</b> {e(m.get("reason"))}<ul>{cands}</ul></div>'
    else:
        c = m["candidates"][m["chosen"]]
        conf = "confirmed by you" if m.get("owner_confirmed") else "not yet confirmed"
        match_html = (f'<p class="meta">Matched to {e(c["address"])} (score {c["score"]:.0f}; {e(c.get("addr_type"))}); {conf}. '
                      f'<form class="inline" method="post" action="/house/{e(p.house_id)}/answer"><input type="hidden" name="field" value="owner_confirms_match"><input type="hidden" name="value" value="yes"><button class="quiet">Confirm match</button></form></p>')
    rows = []
    for name in p.fields:
        f = p.get(name)
        val = '<span class="unknown">unknown</span>' + (f' <span class="limits">— {e(f.note)}</span>' if f.is_unknown and f.note else "") if f.is_unknown else e(fmt(f.value)) + (f" {e(f.units)}" if f.units else "")
        extra = ""
        if f.conflicts:
            extra += f'<div class="limits">conflict kept: {e([c.get("value") for c in f.conflicts])}</div>'
        if f.history:
            extra += f'<div class="limits">history: {e([(h.get("value"), h.get("source_id")) for h in f.history])}</div>'
        rows.append(f"<tr><td>{e(_label(name))}</td><td>{val} {tag(f)}{extra}</td></tr>")
    overlays = []
    for name in p.overlays:
        f = p.get(name)
        val = f'<span class="unknown">unknown</span> <span class="limits">— {e(f.note)}</span>' if f.is_unknown else e(fmt(f.value))
        overlays.append(f"<tr><td>{e(_label(name))}</td><td>{val} {tag(f)}" + (f'<div class="limits">{e(f.limitations)}</div>' if f.limitations else "") + "</td></tr>")
    eq = "".join(f"<tr><td>{e(x['component'])}</td><td>{e(x.get('make',''))} {e(x.get('model',''))} · installed {e(x.get('installed_year') or '?')} · manual {e(x.get('manual_source_id') or 'none')} <span class='tag'>{e(x['status'])}</span></td></tr>" for x in p.equipment)
    fn = "".join(f"<tr><td>{e(x['component'])}</td><td>{e(x['description'])} <span class='tag'>{e(x['severity'])}</span><span class='tag'>{e(x['status'])}</span> <span class='limits'>{e(x['source_doc'])}</span></td></tr>" for x in p.findings)
    rs = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k, v in p.responsibilities.items())
    hid = e(p.house_id)
    forms = f"""
<h2>Add to the record</h2>
<h3>Equipment</h3>
<form method="post" action="/house/{hid}/equipment" class="row"><select name="component"><option>furnace</option><option>ac</option><option>water_heater</option><option>sump_pump</option><option>roof</option></select>
<input name="make" placeholder="make" size="10"> <input name="model" placeholder="model" size="10"> <input name="year" placeholder="year" size="5" inputmode="numeric">
<select name="manual"><option value="">manual: none on file</option><option>goodman_rs6612023</option><option>carrier_58d_u_9sm</option><option>bradford_white_io</option><option>aosmith_100398943</option><option>zoeller_fm2676</option><option>liberty_7035000</option></select>
<button>Record equipment</button></form>
<p class="limits">A replacement retires the previous unit and resets age-based planning; a current-year install adds the warranty-registration deadline.</p>
<h3>Documented finding (from the inspection report)</h3>
<form method="post" action="/house/{hid}/finding" class="row"><input name="component" placeholder="component (roof, electrical…)" size="16" required>
<select name="severity"><option>safety</option><option>major</option><option>minor</option><option>info</option></select>
<input name="description" placeholder="what the report says" size="32" required> <input name="source" placeholder="report p." size="10"> <input type="date" name="date" aria-label="observed date"> <button>Record finding</button></form>
<h3>Responsibility</h3>
<form method="post" action="/house/{hid}/responsibility" class="row"><input name="component" placeholder="component" size="14" required> <input name="party" placeholder="HOA / landlord / homeowner" size="18" required> <input name="reason" placeholder="reason" size="18"> <button>Assign</button></form>"""
    body = f"""<div class="cols">{rail(p)}<div>
{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>House record</h1>{match_html}
<h2>Property</h2><table class="fields">{''.join(rows)}</table>
<h2>Equipment</h2><table class="fields">{eq or '<tr><td colspan=2 class=gap>none recorded</td></tr>'}</table>
<h2>Documented findings</h2><table class="fields">{fn or '<tr><td colspan=2 class=gap>none recorded — enter them from the inspection report below</td></tr>'}</table>
<h2>Responsibilities</h2><table class="fields">{rs or '<tr><td colspan=2 class=gap>homeowner for everything</td></tr>'}</table>
<h2>Regional exposure <span class="limits">(describes the area, not this house)</span></h2><table class="fields">{''.join(overlays)}</table>
{forms}
<p class="row"><a class="btn quiet" href="/house/{hid}/export.json">Export record (JSON)</a> <form class="inline" method="post" action="/house/{hid}/purge" onsubmit="return confirm('Remove documents, completions, findings, estimates and your answers from this record?')"><button class="quiet">Remove private information</button></form></p>
</div></div>"""
    return page(f"{p.house_id} — record", body, nav=nav_for(p, "record"))


def plan_page(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    live = rules.prioritize(tasks)
    top = live[:3]
    nxt = "".join(f'<li><p class="title">{e(t.title)}</p><p class="why">{e(t.why)}</p><p class="meta">{e(_priority_line(t))}</p></li>' for t in top)
    groups = [("finding", "Documented findings"), ("applies", "Applies now"), ("verification", "Verify first"), ("needs_info", "Needs an answer"),
              ("snoozed", "Snoozed"), ("dismissed", "Marked does-not-apply"), ("done", "Done (one-time)"),
              ("someone_else", "Someone else's responsibility"), ("excluded", "Excluded by confirmed information"), ("not_applicable", "Not applicable (data gap)")]
    sections = []
    for st, label in groups:
        items = [t for t in (live if st in ("finding", "applies", "verification", "needs_info") else tasks) if t.status == st]
        if items:
            sections.append(f"<h2>{e(label)} <span class='limits'>({len(items)})</span></h2>" + "".join(task_block(p, t, actions_on=not snapshot) for t in items))
    qs = questions.pending(p, tasks)
    qh = ""
    for q in qs:
        unb = f" <span class='limits'>unblocks {e(', '.join(q['unblocks']))}</span>" if q["unblocks"] else ""
        qh += f"""<div class="q"><form method="post" action="/house/{e(p.house_id)}/answer"><input type="hidden" name="field" value="{e(q['field'])}">
<label>{e(q['question'])}{unb}<br><span class="because">{e(q['matters_because'])}</span></label>
<div class="row"><input name="value" placeholder="{e(q['answer'])}" size="22"> <input name="reason" placeholder="source (invoice, report p.)" size="20"> <button class="quiet">Save</button></div></form></div>"""
    body = f"""<div class="cols">{rail(p)}<div>
{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>What deserves your attention next</h1>
<ol class="next">{nxt or '<li><p class="title gap">Nothing open.</p></li>'}</ol>
<p class="row"><a class="btn" href="/house/{e(p.house_id)}/fit">With limited time and money…</a> <a class="btn quiet" href="/house/{e(p.house_id)}/reminders.ics">Download calendar (.ics)</a></p>
<h2>Questions that could change this plan <span class="limits">({len(qs)})</span></h2>
<p class="limits">Only fields still unknown are asked. Answering "unknown" keeps the field open; it never counts as done.</p>{qh or '<p class="gap">No open questions.</p>'}
{''.join(sections)}
</div></div>"""
    return page(f"{p.house_id} — plan", body, nav=nav_for(p, "plan"), snapshot=snapshot)


def fit_page(p: Profile, hours: float, dollars: float) -> str:
    txt = reports.constrained(p, rules.evaluate(p), hours=hours, dollars=dollars)
    body = f"""<div><h1>With limited time and money</h1>
<form method="get" class="row"><label>Hours <input name="hours" value="{hours:g}" size="4" inputmode="decimal"></label> <label>Dollars <input name="dollars" value="{dollars:g}" size="6" inputmode="decimal"></label> <button class="primary">Show what fits</button></form>
<pre class="doc">{e(txt)}</pre></div>"""
    return page(f"{p.house_id} — fit", body, nav=nav_for(p, "today"))


def reports_page(p: Profile, kind: str, *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    kinds = [("buy", "Before you buy"), ("plan90", "First 90 days"), ("next", "Next three"), ("calendar", "12-month calendar")]
    fn = {"buy": reports.before_you_buy, "plan90": reports.first_90_days, "next": reports.next_three, "calendar": reports.calendar}[kind]
    tabs = " ".join(f'<a class="btn {"" if k == kind else "quiet"}" href="/house/{e(p.house_id)}/reports?kind={k}">{e(l)}</a>' for k, l in kinds)
    body = f"""<div class="cols">{rail(p)}<div><h1>Reports</h1><p class="row">{tabs}</p>
<p class="limits">Every report is a view over the same house record; a correction changes all of them.</p>
<pre class="doc">{e(fn(p, tasks))}</pre></div></div>"""
    return page(f"{p.house_id} — reports", body, nav=nav_for(p, "reports"), snapshot=snapshot)


def budget_page(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    b = budget.build_budgets(p, tasks)
    def money(x): return f"${x:,.0f}"
    r1 = "".join(f"<tr><td>{e(i['task'])}</td><td>×{i['per_year']:.1f}/yr</td><td>{'your time only' if i['basis']=='none' else money(i['low'])+'–'+money(i['high'])+'/yr'}</td><td>{e(i['basis'])} · {e(i['source'])} {e(i['date'])}</td></tr>" for i in b["routine"])
    r2 = "".join(f"<tr><td>{e(i['task'])}<div class='limits'>scope: {e(i['scope'])}{(' · excludes: ' + e(i['exclusions'])) if i['exclusions'] else ''}</div></td><td></td><td>{money(i['low'])}–{money(i['high'])}</td><td>{e(i['basis'])} · {e(i['source'])} {e(i['date'])} · {e(i['geo'])}</td></tr>" for i in b["repairs"])
    r3 = "".join(f"<tr><td>{e(i['component'])}{('<div class=limits>' + e(i['overlap_note']) + '</div>') if i.get('overlap_note') else ''}</td><td>over {i['years']} yr</td><td>{money(i['low'])}–{money(i['high'])}<br>{money(i['monthly_low'])}–{money(i['monthly_high'])}/month</td><td>{e(i['basis'])} · {e(i['source'])} {e(i['date'])}</td></tr>" for i in b["replacements"])
    un = "".join(f"<tr><td>{e(u['budget'])}</td><td>{e(u['task'])}</td><td>{e(u['why'])}</td></tr>" for u in b["unknown"])
    t = b["totals"]
    hid = e(p.house_id)
    body = f"""<div class="cols">{rail(p)}<div>{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>Three budgets</h1><p class="limits">{e(b['note'])}</p>
<h2>Routine maintenance <span class="limits">priced items {money(t['routine_per_year'][0])}–{money(t['routine_per_year'][1])} per year</span></h2>
<div class="tbl"><table class="b"><tr><th>Task</th><th>Cadence</th><th>Range</th><th>Basis</th></tr>{r1 or '<tr><td colspan=4 class=gap>nothing priced yet</td></tr>'}</table></div>
<h2>Known repairs <span class="limits">priced items {money(t['repairs'][0])}–{money(t['repairs'][1])}</span></h2>
<div class="tbl"><table class="b"><tr><th>Finding</th><th></th><th>Range</th><th>Basis</th></tr>{r2 or '<tr><td colspan=4 class=gap>no quotes on file</td></tr>'}</table></div>
<h2>Future replacements <span class="limits">reserve {money(t['replacement_reserve_per_month'][0])}–{money(t['replacement_reserve_per_month'][1])} per month</span></h2>
<p class="limits">Average service life is not a failure date. You choose the planning period and the range.</p>
<div class="tbl"><table class="b"><tr><th>Component</th><th>Period</th><th>Range / monthly</th><th>Basis</th></tr>{r3 or '<tr><td colspan=4 class=gap>no reserve scenarios yet</td></tr>'}</table></div>
<h2>Unpriced <span class="limits">not in any total</span></h2>
<div class="tbl"><table class="b"><tr><th>Budget</th><th>Task</th><th>What would price it</th></tr>{un or '<tr><td colspan=3 class=gap>everything live is priced</td></tr>'}</table></div>
<h2>Record a quote or reference</h2>
<form method="post" action="/house/{hid}/quote" class="row"><input name="applies_to" placeholder="rule id or component" size="18" required> <input name="low" placeholder="low $" size="7" required> <input name="high" placeholder="high $" size="7" required>
<select name="basis"><option>user_quote</option><option>published_reference</option><option>planning_assumption</option></select> <input name="scope" placeholder="scope" size="22" required> <input name="exclusions" placeholder="exclusions" size="14"> <input name="source" placeholder="source" size="14"> <button>Save estimate</button></form>
<h2>Choose a replacement reserve scenario</h2>
<form method="post" action="/house/{hid}/reserve" class="row"><input name="component" placeholder="component" size="12" required> <input name="years" placeholder="years" size="5" required> <input name="low" placeholder="low $" size="7" required> <input name="high" placeholder="high $" size="7" required>
<select name="basis"><option>planning_assumption</option><option>user_quote</option><option>published_reference</option></select> <button>Save scenario</button></form>
</div></div>"""
    return page(f"{p.house_id} — budgets", body, nav=nav_for(p, "budget"), snapshot=snapshot)


def history_page(p: Profile, *, snapshot: bool = False) -> str:
    hid = e(p.house_id)
    body = f"""<div class="cols">{rail(p)}<div><h1>House history</h1>
<pre class="doc">{e(actions.history(p))}</pre>
<h2>Record a document reference</h2>
<form method="post" action="/house/{hid}/document" class="row"><select name="kind"><option>invoice</option><option>manual</option><option>warranty</option><option>photo</option><option>report</option><option>permit</option><option>other</option></select>
<input name="title" placeholder="title" size="24" required> <input name="ref" placeholder="where you keep it (path or link)" size="30" required> <input name="component" placeholder="component" size="12"> <button>Save reference</button></form>
<p class="limits">Only the reference is stored; the file stays where you keep it.</p>
<h2>Upcoming reminders</h2><pre class="doc">{e(reminders.render_upcoming(p, 90))}</pre>
<p><a class="btn" href="/house/{hid}/reminders.ics">Download calendar (.ics)</a></p><pre class="doc">{e(reminders.METHOD_STATEMENT)}</pre>
</div></div>"""
    return page(f"{p.house_id} — history", body, nav=nav_for(p, "history"), snapshot=snapshot)


def providers_page(p: Profile, t: rules.Task) -> str:
    m = providers.match(p, t)
    body = f"""<div><h1>Who could do this: {e(t.title)}</h1>
<pre class="doc">{e(providers.render_match(m, p))}</pre>
<p class="limits">Registration is never presented as proof of competence. Workmanship evidence is unavailable from any permitted source. HomeKeeper does not contact providers.</p></div>"""
    return page(f"{p.house_id} — providers", body, nav=nav_for(p, "tasks"))


def brief_page(p: Profile, t: rules.Task) -> str:
    from . import briefs
    txt = briefs.brief_text(p, t)
    body = f"""<div><h1>Job brief</h1><p class="limits">Editable: copy this into an email or document. Facts come from the house record; nothing here is a diagnosis.</p>
<textarea rows="34" style="width:100%" class="ui">{e(txt)}</textarea>
<form method="post" action="/house/{e(p.house_id)}/brief"><input type="hidden" name="task" value="{e(t.rule_id)}"><button class="quiet">Save a copy under houses/{e(p.house_id)}/briefs</button></form></div>"""
    return page(f"{p.house_id} — brief", body, nav=nav_for(p, "tasks"))
