"""One-page house experience: understand my house → see what matters → take action → record → know what comes next.

Sections, in that order, on a single page with an in-page nav:
  #now      identity + status, attention (if any), next actions, questions that would change the plan
  #upcoming preview of the next 60 days and money at a glance
  #house    the record, editable in place; equipment, findings, responsibilities, area
  #history  work done, documents, calendar file
Every task is one line + one button; details expand in place (why, how, DIY/pro, equipment, evidence,
providers, brief, history). Actions return to the same task (#anchor) with a message and an undo.
Reuses CSS, tags and helpers from hk.web / hk.web2.
"""
from __future__ import annotations

import datetime as _dt
import html
import re

from . import actions, budget, providers, questions, reminders, rules
from .evidence import Profile
from .web import CSS, EV_TAG, e, fmt, page as _page, tag
from .web2 import EXTRA_CSS, _addr, _plain_why, _question, _rows, _area_text, ABOUT, SYSTEMS, AREA, DETAILS, landing, onboarding
from .briefs import brief_text

CSS3 = """
.pnav{position:sticky;top:0;background:var(--paper);border-bottom:1px solid var(--mortar);z-index:2;padding:.45rem 16px;display:flex;gap:1.1rem;font-family:"Segoe UI",system-ui,sans-serif;font-size:.9rem;overflow-x:auto;white-space:nowrap}
.pnav a{color:var(--ink-2);text-decoration:none;padding:.15rem 0}.pnav a:hover{color:var(--ink)}
section.s{margin:2.2rem 0 0;scroll-margin-top:3.2rem}
section.s>h2{margin:0 0 .8rem;font-size:1.3rem}
.ident{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;flex-wrap:wrap;margin:.6rem 0 .4rem}
.ident h1{margin:0;font-size:1.9rem;max-width:26ch}
.ident .status{font-family:"Segoe UI",system-ui,sans-serif;font-size:.88rem;color:var(--ink-2);max-width:26rem}
.ident .status b{color:var(--ink);font-weight:500}
.attn{border:1px solid var(--brick);border-left-width:5px;padding:.7rem 1rem;margin:1rem 0;background:var(--chalk)}
.attn h2{margin:0 0 .3rem;font-size:1.05rem;font-family:"Segoe UI",system-ui,sans-serif;font-weight:600;color:var(--brick)}
.attn ul{margin:.2rem 0 0;padding-left:1.1rem}.attn li{margin:.15rem 0}
.tl{list-style:none;padding:0;margin:0}
.tl>li{scroll-margin-top:3.4rem;border-top:1px solid var(--mortar);padding:.75rem 0}
.tl>li.first{border-top:2px solid var(--ink)}
.trow{display:grid;grid-template-columns:1.4rem minmax(0,1fr) auto;gap:.3rem .7rem;align-items:start}
.trow .ic{color:var(--ink-2);padding-top:.25rem}.trow .ic.safety{color:var(--brick)}.trow .ic.done{color:var(--verdigris)}
.tl{max-width:56rem}
.trow .ttl{margin:0;font-size:1.12rem;line-height:1.3}
.trow .sub{grid-column:2;margin:.1rem 0 0;font-size:.86rem;color:var(--ink-2);font-family:"Segoe UI",system-ui,sans-serif}
.trow .sub .when{color:var(--ink)}
.trow .sub .warn{color:var(--brick)}
.trow .do{grid-column:3;grid-row:1/span 2;display:flex;flex-direction:column;align-items:flex-end;gap:.3rem}
.trow .do form{margin:0}
.trow details{grid-column:2;margin:.35rem 0 0}
.trow details>summary{list-style:none;font-size:.86rem;color:var(--ink-2);display:inline-flex;align-items:center;gap:.3rem}
.trow details>summary::-webkit-details-marker{display:none}
.trow details>summary::before{content:"";display:inline-block;width:.4rem;height:.4rem;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(-45deg) translate(-1px,-1px);transition:transform .15s;margin-right:.1rem}
.trow details[open]>summary::before{transform:rotate(45deg) translate(-2px,-2px)}
@media(prefers-reduced-motion:reduce){.trow details>summary::before{transition:none}}
.panel{margin:.6rem 0 .2rem;padding:.8rem 1rem;background:var(--chalk);border:1px solid var(--mortar);border-radius:4px;font-size:.95rem}
.panel h4{margin:.7rem 0 .2rem;font-family:"Segoe UI",system-ui,sans-serif;font-size:.8rem;color:var(--ink-2);font-weight:600}
.panel h4:first-child{margin-top:0}
.panel p{margin:.2rem 0}
.panel .opts{display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;margin:.4rem 0}
.panel .opts form{display:inline}
.panel .pv{border-top:1px solid var(--mortar);padding:.4rem 0}
.panel .pv b{font-weight:500}
.panel .pv .cred{display:block;font-size:.84rem;color:var(--ink-2)}
.chip{font-size:.82rem;padding:.25rem .6rem;border:1px solid var(--mortar);background:var(--paper);border-radius:999px;cursor:pointer;color:var(--ink)}
.chip:hover{border-color:var(--ink)}
.flash{position:relative;border:1px solid var(--verdigris);border-left-width:5px;background:var(--chalk);padding:.6rem .9rem;margin:.8rem 0;font-size:.92rem}
.flash form{display:inline;margin-left:.4rem}
.flash.err{border-color:var(--brick)}
.prev{display:grid;grid-template-columns:minmax(0,1fr);gap:1.5rem}
@media(min-width:800px){.prev{grid-template-columns:1fr 1fr}}
.prev h3{margin:0 0 .4rem}
.up li{margin:.2rem 0;font-size:.95rem}.up .d{color:var(--ink-2);font-family:"Segoe UI",system-ui,sans-serif;font-size:.82rem;margin-right:.4rem}
.kv{font-size:.95rem}.kv div{display:flex;justify-content:space-between;gap:1rem;padding:.3rem 0;border-top:1px solid var(--mortar)}
.kv div:first-child{border-top:0}.kv .v{font-family:"Segoe UI",system-ui,sans-serif;white-space:nowrap}
.fields td .edit{display:inline-block;margin-left:.4rem}
.fields details.ed{display:inline-block;margin:0}.fields details.ed summary{display:inline;font-size:.8rem;color:var(--ink-2);text-decoration:underline;cursor:pointer}
.fields details.ed form{display:flex;gap:.4rem;flex-wrap:wrap;margin:.3rem 0 0}
.gq{border-top:1px solid var(--mortar);padding:.7rem 0}
.sr-only{position:absolute;left:-9999px}
.btn.sm,button.sm{font-size:.8rem;padding:.25rem .55rem}
.ghost{background:transparent}
.sect-note{font-size:.88rem;color:var(--ink-2);margin:0 0 .6rem}
.group summary{padding:.4rem 0}
.empty{color:var(--ink-2);font-style:italic;padding:.4rem 0}
@media(max-width:640px){.trow{grid-template-columns:1.2rem minmax(0,1fr) auto}.trow .do{grid-column:3;grid-row:1}.trow .sub,.trow details{grid-column:2/span 2}.ident h1{font-size:1.5rem}.pnav{gap:.9rem}.btn,button{min-height:2.4rem}}
.attn ul{list-style:none;padding:0}.attn li{padding:.25rem 0;border-top:1px solid var(--mortar)}.attn li:first-child{border-top:0}
"""

ICONS = {
    "alert": '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M8 2.2 14.5 13.5H1.5Z" stroke-linejoin="round"/><path d="M8 6.5v3.2M8 11.8v.2"/></svg>',
    "clock": '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="6"/><path d="M8 4.5V8l2.4 1.5"/></svg>',
    "check": '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M3 8.5l3 3 7-7" stroke-linecap="round" stroke-linejoin="round"/></svg>',
    "wrench": '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M10.5 2.5a3 3 0 0 0-3.2 4.2L2.5 11.5l2 2 4.8-4.8a3 3 0 0 0 4.2-3.2l-1.8 1.8-1.7-.5-.5-1.7Z" stroke-linejoin="round"/></svg>',
    "q": '<svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><circle cx="8" cy="8" r="6"/><path d="M6.2 6.3a1.9 1.9 0 1 1 2.6 1.8c-.6.3-.8.6-.8 1.2M8 11.6v.2"/></svg>',
}


def page(title, body, *, pnav=True, snapshot=False):
    nav = ('<nav class="pnav" aria-label="Sections"><a href="#now">Now</a><a href="#upcoming">Upcoming</a><a href="#house">House</a>'
           '<a href="#history">History</a><a href="/owner" style="margin-left:auto">All houses</a></nav>') if pnav else ""
    html_ = _page(title, body, nav=[], snapshot=snapshot).replace("</style>", EXTRA_CSS + CSS3 + "</style>", 1)
    html_ = html_.replace('<header class="top">', '<header class="top" style="padding-bottom:.6rem">', 1)
    return html_.replace("<main>", nav + "<main>", 1)


# ---------------------------------------------------------------- flash with undo
def flash_html(msg: str, p: Profile) -> str:
    if not msg:
        return ""
    m = re.match(r"^\[undo:(.+?)\](.*)$", msg, re.S)
    undo = ""
    text = msg
    if m:
        rid, text = m.group(1), m.group(2)
        undo = (f'<form method="post" action="/house/{e(p.house_id)}/undo"><input type="hidden" name="task" value="{e(rid)}">'
                f'<button class="sm quiet">Undo</button></form>')
    cls = "flash err" if text.lower().startswith(("could not", "no ", "type ")) else "flash"
    return f'<div class="{cls}" role="status">{e(text)}{undo}</div>'


# ---------------------------------------------------------------- task rendering
def _when(t: rules.Task) -> tuple[str, bool]:
    d = t.due or ""
    if t.status == "finding":
        return ("From your inspection", t.severity == "safety")
    if d.startswith("overdue"):
        return ("Overdue", True)
    if d.startswith("due now"):
        return ("Due now", False)
    if d.startswith("next due"):
        m = re.search(r"next due (\d{4}-\d{2}-\d{2})", d)
        return (f"Next {m.group(1)}" if m else "Later", False)
    if "window closes" in d:
        m = re.search(r"closes (\d{4}-\d{2}-\d{2})", d)
        return (f"Best before {m.group(1)}" if m else "This season", False)
    if d.startswith("next window"):
        m = re.search(r"next window (\d{4}-\d{2}-\d{2})", d)
        return (f"From {m.group(1)}" if m else "Later", False)
    if d.startswith("by "):
        return (d.replace("by ", "By "), False)
    if t.status == "verification":
        return ("Quick check", False)
    if t.status == "needs_info":
        return ("Needs an answer", False)
    return ("Open", False)


def _attn_reason(t: rules.Task, closing) -> str:
    if t.status == "finding":
        return "a safety item in your inspection report"
    if (t.due or "").startswith("overdue"):
        return "overdue"
    if closing:
        return f"closing is {(closing - _dt.date.today()).days} days away"
    return ""


def _who(t: rules.Task) -> str:
    return {"diy": "you can do it", "pro": "needs a pro", "diy_or_pro": "you or a pro", "verification": "a quick check",
            "planning": "planning"}.get(t.diy_pro, "")


def _effort(t: rules.Task) -> str:
    x = (t.effort or "").replace("1 visit", "one visit")
    if not x or x.startswith("depends") or x.startswith("planning") or x == "reading":
        return ""
    return f"about {x}" if x[0].isdigit() and "visit" not in x else x


def _icon(t: rules.Task) -> str:
    if (t.status == "finding" and t.severity == "safety") or (t.due or "").startswith("overdue"):
        return f'<span class="ic safety">{ICONS["alert"]}</span>'
    if t.severity == "safety" or t.status == "finding":
        return f'<span class="ic">{ICONS["alert"]}</span>'
    if t.diy_pro == "pro":
        return f'<span class="ic">{ICONS["wrench"]}</span>'
    if t.status in ("needs_info", "verification"):
        return f'<span class="ic">{ICONS["q"]}</span>'
    return f'<span class="ic">{ICONS["clock"]}</span>'


def _primary(p: Profile, t: rules.Task) -> str:
    hid, rid = e(p.house_id), e(t.rule_id)
    if t.status == "needs_info":
        return f'<a class="btn sm" href="#q-{e(t.missing[0].split(".")[0] if t.missing else "")}">Answer</a>'
    if t.status == "verification":
        return (f'<form method="post" action="/house/{hid}/done"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}">'
                f'<button class="primary sm">Checked</button></form>')
    return (f'<form method="post" action="/house/{hid}/done"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}">'
            f'<button class="primary sm">Done</button></form>')


def _provider_html(p: Profile, t: rules.Task) -> str:
    if not t.provider_category:
        return ""
    m = providers.match(p, t, max_results=4)
    rows = []
    for r in m["matches"]:
        pr = r["provider"]
        serves = {True: "serves your area", False: "outside their stated area", None: "service area unknown"}[r["serves"]]
        creds = "".join(f'<span class="cred">{e(providers.wording(c))}</span>' for c in r["credentials"]) or '<span class="cred">no credential verified</span>'
        dist = f" · {r['distance_mi']:.1f} mi" if r["distance_mi"] is not None else ""
        syn = " (demo)" if pr.get("synthetic") else ""
        rows.append(f'<div class="pv"><b>{e(pr["name"])}{syn}</b> <span class="limits">{e(serves)}{dist}{(" · " + e(pr["phone"])) if pr.get("phone") else ""}</span>{creds}</div>')
    body = "".join(rows) or f'<p class="empty">No one on file yet for this kind of work.</p>'
    gap = f'<p class="limits">{e(m["gap"])}</p>' if m["gap"] else ""
    return (f'<h4>Who could do this ({e(t.provider_category.replace("_", " "))})</h4>{body}{gap}'
            f'<p class="limits">Listed credentials are quoted from their source with the date checked. A registration is not proof of skill; '
            f'no permitted source rates workmanship. <a href="/house/{e(p.house_id)}/providers/{e(t.rule_id)}">Full list and hiring checklist</a></p>')


def task_item(p: Profile, t: rules.Task, *, first: bool = False, snapshot: bool = False, open_: bool = False) -> str:
    hid, rid = e(p.house_id), e(t.rule_id)
    when, warn = _when(t)
    bits = [f'<span class="when{" warn" if warn else ""}">{e(when)}</span>']
    for x in (_effort(t), _who(t)):
        if x:
            bits.append(e(x))
    if (t.cost or {}).get("basis") == "none":
        bits.append("no cost")
    if t.delay_consequence and (t.severity in ("safety", "health", "deadline") or t.status == "finding"):
        cls = "warn" if (t.status == "finding" and t.severity == "safety") or warn else ""
        bits.append(f'<span class="{cls}">if delayed: {e(t.delay_consequence[:90])}{"…" if len(t.delay_consequence) > 90 else ""}</span>')
    sub = " · ".join(bits)
    primary = "" if snapshot else _primary(p, t)
    # details panel
    comps = [c for c in (getattr(p, "completions", None) or []) if c["rule_id"] == t.rule_id]
    eq = p.installed(rules.load_rules() and next((r.get("equipment_component", "") for r in rules.load_rules() if r["id"] == t.rule_id), "") or "")
    ev = "".join(f'<li>{e(x["field"].replace("_", " "))}: {e(fmt(x["value"])) if x["value"] is not None else "<span class=unknown>unknown</span>"} '
                 f'<span class="tag {EV_TAG.get(x["evidence_type"], ("", "unk"))[1]}">{e(EV_TAG.get(x["evidence_type"], (x["evidence_type"], ""))[0])}</span></li>' for x in t.evidence)
    src = "".join(f"<li>{e(s['source_id'].replace('_', ' '))}: {e(s['ref'])}</li>" for s in t.sources)
    opts = "" if snapshot else f"""
<h4>Other options</h4><div class="opts">
<form method="post" action="/house/{hid}/snooze"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input type="hidden" name="days" value="7"><button class="chip">Remind me in a week</button></form>
<form method="post" action="/house/{hid}/snooze"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input type="hidden" name="days" value="30"><button class="chip">In a month</button></form>
<form method="post" action="/house/{hid}/snooze"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><label class="limits">Until <input type="date" name="until" aria-label="postpone until" style="padding:.15rem .3rem"></label> <button class="chip">Set</button></form>
</div><div class="opts">
<form method="post" action="/house/{hid}/dismiss"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input type="hidden" name="reason" value="already done before I bought the house"><button class="chip">Already done</button></form>
<form method="post" action="/house/{hid}/dismiss"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input type="hidden" name="reason" value="this house doesn't have that"><button class="chip">House doesn't have this</button></form>
<form method="post" action="/house/{hid}/dismiss"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input type="hidden" name="reason" value="someone else is responsible"><button class="chip">Someone else handles it</button></form>
<form method="post" action="/house/{hid}/dismiss"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><input name="reason" placeholder="another reason" size="18" required aria-label="reason it does not apply"> <button class="chip">Doesn't apply</button></form>
</div>
<h4>Record details with it (optional)</h4>
<form method="post" action="/house/{hid}/done" class="opts"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}">
<label class="limits">Date <input type="date" name="date" value="{_dt.date.today().isoformat()}"></label> <input name="cost" placeholder="cost $" size="7" inputmode="decimal" aria-label="cost"> <input name="contractor" placeholder="who did it" size="14" aria-label="who did it"> <input name="notes" placeholder="notes" size="18" aria-label="notes"> <button class="sm">Save as done</button></form>"""
    brief = "" if snapshot or t.diy_pro not in ("pro", "diy_or_pro") and t.status != "finding" else \
        f'<h4>Hiring someone</h4><p><a href="/house/{hid}/brief/{rid}">Open the job brief</a> — an editable note with what the record knows, the questions to ask, and what a comparable quote must state.</p>'
    eq_html = (f'<h4>Your equipment</h4><p>{e(eq.get("make", ""))} {e(eq.get("model", ""))} · installed {e(eq.get("installed_year") or "?")}'
               f'{(" · last service " + e(eq["last_service_date"])) if eq.get("last_service_date") else ""}'
               f'{" · interval from its manual" if t.refined_by and "—" in t.refined_by else ""}</p>') if eq else ""
    hist_items = []
    for c in sorted(comps, key=lambda c: c["date"], reverse=True)[:5]:
        line = e(c["date"])
        if c.get("notes"):
            line += " — " + e(c["notes"])
        if c.get("contractor"):
            line += " (" + e(c["contractor"]) + ")"
        hist_items.append("<li>" + line + "</li>")
    hist = ("<h4>Done before</h4><ul>" + "".join(hist_items) + "</ul>") if hist_items else ""
    panel = f"""<div class="panel">
<h4>Why it applies to this house</h4><p>{e(_plain_why(t))}</p>
<h4>What to do</h4><p>{e(t.action)}</p>
{f'<h4>Before you start</h4><p>{e(t.safe_observation)}</p>' if t.safe_observation else ''}
{f'<h4>Call a professional if</h4><p>{e(t.pro_conditions)}</p>' if t.pro_conditions else ''}
<h4>Done when</h4><p>{e(t.completion_criteria or "you've recorded it")}{(" · keep: " + e(t.retain)) if t.retain else ""}</p>
{eq_html}{hist}{_provider_html(p, t) if t.provider_category and t.status != "needs_info" else ""}{brief}
<details><summary>Evidence and sources</summary><div class="ev"><p>Because: {e(t.reason)}</p><ul>{ev or '<li class=empty>none</li>'}</ul><p>Sources:</p><ul>{src}</ul></div></details>
{opts}</div>"""
    return f"""<li id="{rid}" class="{'first' if first else ''}"><div class="trow">{_icon(t)}<p class="ttl">{e(t.title)}</p>
<div class="do">{primary}</div>
<p class="sub">{sub}</p>
<details{" open" if open_ else ""}><summary>Details</summary>{panel}</details></div></li>"""


def _quiet_item(p: Profile, t: rules.Task, snapshot: bool) -> str:
    hid, rid = e(p.house_id), e(t.rule_id)
    reason = {"snoozed": t.reason.replace("snoozed", "postponed"), "dismissed": t.reason.replace("owner: does not apply — ", "").replace(" (not counted as done)", ""),
              "done": "done", "someone_else": t.reason, "excluded": t.reason.replace("excluded because ", "").replace(" (confirmed information)", ""),
              "not_applicable": "waiting on data: " + t.reason}.get(t.status, t.reason)
    undo = "" if snapshot or t.status not in ("snoozed", "dismissed") else \
        f'<form method="post" action="/house/{hid}/reopen" style="display:inline"><input type="hidden" name="task" value="{rid}"><input type="hidden" name="back" value="{rid}"><button class="sm quiet">Bring back</button></form>'
    return f'<li id="{rid}"><div class="trow"><span class="ic{" done" if t.status == "done" else ""}">{ICONS["check"] if t.status == "done" else ""}</span><p class="ttl" style="font-size:1rem;color:var(--ink-2)">{e(t.title)}</p><div class="do">{undo}</div><p class="sub">{e(reason)}</p></div></li>'


# ---------------------------------------------------------------- the page
def house_page(p: Profile, msg: str = "", *, snapshot: bool = False, open_task: str = "") -> str:
    tasks = rules.evaluate(p)
    live = rules.prioritize(tasks)
    hid = e(p.house_id)
    # identity + status
    stage = p.value("stage")
    status_bits = []
    if p.value("year_built"): status_bits.append(f"built <b>{e(p.value('year_built'))}</b>")
    if p.value("basement"): status_bits.append(f"<b>{e(p.value('basement')).lower()}</b> basement")
    if p.value("municipality"): status_bits.append(f"<b>{e(p.value('municipality'))}</b>")
    if stage == "under_contract":
        status_bits.append("under contract" + (f", closing <b>{e(p.value('closing_date'))}</b>" if p.value("closing_date") else ""))
    elif stage == "before_buy":
        status_bits.append("a home you're considering")
    else:
        status_bits.append("you own it")
    m = p.match
    match_line = ""
    if m.get("ambiguous") or m.get("chosen") is None:
        match_line = f'<p class="limits"><a href="/house/{hid}/start">Which address did you mean? Choose one</a></p>'
    elif not m.get("owner_confirmed") and not snapshot:
        matched = e(m["candidates"][m["chosen"]]["address"])
        match_line = ('<form class="inline" method="post" action="/house/' + hid + '/answer"><input type="hidden" name="field" value="owner_confirms_match"><input type="hidden" name="value" value="yes">'
                      '<span class="limits">Matched to ' + matched + ' — </span><button class="sm quiet">that&#39;s right</button> <a class="limits" href="/owner">not my house</a></form>')
    # attention: safety findings, overdue, deadlines within 30 days
    closing = None
    try:
        closing = _dt.date.fromisoformat(str(p.value("closing_date"))[:10]) if p.value("closing_date") else None
    except ValueError:
        closing = None
    deadline_soon = closing is not None and 0 <= (closing - _dt.date.today()).days <= 30
    attn = [t for t in live if (t.status == "finding" and t.severity == "safety") or (t.due or "").startswith("overdue")
            or (deadline_soon and t.severity == "deadline" and t.status == "applies")]
    attn_html = ""
    if attn:
        attn_html = ('<div class="attn" role="region" aria-label="Needs attention"><h2>Needs attention</h2><ul>'
                     + "".join(f'<li><a href="#{e(t.rule_id)}">{e(t.title)}</a> <span class="limits">— {e(_attn_reason(t, closing))}</span></li>' for t in attn[:4])
                     + "</ul></div>")
    # next actions: top 3 excluding needs_info; then the rest grouped
    actionable = [t for t in live if t.status != "needs_info"]
    top = actionable[:3]
    rest_now = [t for t in actionable[3:] if not (t.due or "").startswith("next due")]
    later = [t for t in actionable if (t.due or "").startswith("next due")]
    rest_now = [t for t in rest_now if t not in later]
    need = [t for t in live if t.status == "needs_info"]
    quiet = {"snoozed": "Postponed", "dismissed": "Set aside", "done": "Done", "someone_else": "Someone else's", "excluded": "Not relevant to this house", "not_applicable": "Waiting on data"}
    quiet_html = ""
    for st, label in quiet.items():
        items = [t for t in tasks if t.status == st]
        if items:
            quiet_html += f'<details class="group"><summary>{e(label)} <span class="n">({len(items)})</span></summary><ul class="tl">{"".join(_quiet_item(p, t, snapshot) for t in items)}</ul></details>'
    # questions
    qs = questions.pending(p, tasks)
    q_html = ""
    if qs:
        q_html = (f'<h3 style="margin-top:1.6rem">One answer would sharpen this plan</h3>'
                  + "".join(f'<div id="q-{e(q["field"])}">{_question(p, q, next_="now")}</div>' for q in qs[:2])
                  + (f'<details class="group"><summary>{len(qs) - 2} more questions</summary>' + "".join(f'<div id="q-{e(q["field"])}">{_question(p, q, next_="now")}</div>' for q in qs[2:]) + "</details>" if len(qs) > 2 else ""))
    # upcoming + money preview
    today_ = _dt.date.today()
    evs = [ev for ev in reminders.build_events(p, today_) if today_ < ev["date"] <= today_ + _dt.timedelta(days=60)][:8]
    up = "".join(f'<li><span class="d">{ev["date"].strftime("%b %d")}</span>{e(ev["task"].title)}</li>' for ev in evs) or '<li class="empty">nothing scheduled in the next 60 days beyond what is due now</li>'
    b = budget.build_budgets(p, tasks)
    tt = b["totals"]
    def money(x): return f"${x:,.0f}"
    kv = (f'<div><span>Routine upkeep, priced items</span><span class="v">{money(tt["routine_per_year"][0])}–{money(tt["routine_per_year"][1])} / yr</span></div>'
          f'<div><span>Known repairs, quoted</span><span class="v">{money(tt["repairs"][0])}–{money(tt["repairs"][1])}</span></div>'
          f'<div><span>Saving for replacements</span><span class="v">{money(tt["replacement_reserve_per_month"][0])}–{money(tt["replacement_reserve_per_month"][1])} / mo</span></div>'
          f'<div><span>Not priced yet</span><span class="v">{len(b["unknown"])} items</span></div>')
    # house record (editable)
    rec = _house_section(p, snapshot)
    # history
    comps = sorted(getattr(p, "completions", []) or [], key=lambda c: c["date"], reverse=True)
    spend = sum(float(c["cost"]) for c in comps if c.get("cost"))
    titles = {r["id"]: r["title"] for r in rules.load_rules()}
    hist_rows = "".join(f'<li><span class="d">{e(c["date"])}</span>{e(titles.get(c["rule_id"], c["rule_id"]))}'
                        f'{(" — " + e(c["notes"])) if c.get("notes") else ""}{(" · $" + format(c["cost"], ",.0f")) if c.get("cost") else ""}{(" · " + e(c["contractor"])) if c.get("contractor") else ""}</li>' for c in comps[:12])
    docs = getattr(p, "documents", []) or []
    doc_rows = "".join(f'<li>{e(d["kind"])}: {e(d["title"])} <span class="limits">{e(d["ref"])}</span></li>' for d in docs)
    body = f"""{flash_html(msg, p)}
<section class="s" id="now" style="margin-top:.4rem">
<div class="ident"><div><h1>{e(_addr(p))}</h1>{match_line}</div><p class="status">{", ".join(status_bits)}.{' <span class="tag">demo house</span>' if p.synthetic else ''}</p></div>
{attn_html}
<h2>Do next</h2>
<ul class="tl">{"".join(task_item(p, t, first=(i == 0), snapshot=snapshot, open_=(t.rule_id == open_task)) for i, t in enumerate(top)) or '<li class="empty">Nothing open right now.</li>'}</ul>
{f'<details class="group"><summary>{len(rest_now)} more to do</summary><ul class="tl">{"".join(task_item(p, t, snapshot=snapshot, open_=(t.rule_id == open_task)) for t in rest_now)}</ul></details>' if rest_now else ''}
{f'<details class="group"><summary>Recurring, next due later <span class="n">({len(later)})</span></summary><ul class="tl">{"".join(task_item(p, t, snapshot=snapshot, open_=(t.rule_id == open_task)) for t in later)}</ul></details>' if later else ''}
{f'<details class="group"><summary>Waiting on an answer from you <span class="n">({len(need)})</span></summary><ul class="tl">{"".join(task_item(p, t, snapshot=snapshot) for t in need)}</ul></details>' if need else ''}
{quiet_html}
{q_html}
<p class="more" style="margin-top:1.2rem"><a href="/house/{hid}/fit">I have limited time and money</a>{' · <a href="/house/' + hid + '/report/buy">Before-you-buy summary</a>' if stage in ('under_contract', 'before_buy') else ''}</p>
</section>
<section class="s" id="upcoming"><h2>Coming up</h2>
<div class="prev"><div><h3>Next 60 days</h3><ul class="up">{up}</ul><p class="limits"><a href="/house/{hid}/reminders.ics">Add these to my calendar</a> — a file you import; re-download after recording work. <a href="/house/{hid}/report/calendar">Full year</a></p></div>
<div><h3>Money at a glance</h3><div class="kv">{kv}</div><p class="limits">Only prices you entered or references you chose are counted; nothing is estimated for you. <a href="/house/{hid}/money">Add quotes and set-asides</a></p></div></div>
</section>
<section class="s" id="house"><h2>The house</h2>{rec}</section>
<section class="s" id="history"><h2>History</h2>
<div class="prev"><div><h3>Work done <span class="limits">{len(comps)} items · ${spend:,.0f} recorded</span></h3><ul class="up">{hist_rows or '<li class="empty">nothing yet — press Done on a task above</li>'}</ul></div>
<div><h3>Documents</h3><ul class="up">{doc_rows or '<li class="empty">none yet</li>'}</ul>
{'' if snapshot else f'''<details class="group"><summary>Add a document reference</summary><form method="post" action="/house/{hid}/document" class="row"><select name="kind" aria-label="kind"><option>invoice</option><option>manual</option><option>warranty</option><option>photo</option><option>report</option><option>permit</option><option>other</option></select>
<input name="title" placeholder="title" size="20" required aria-label="title"> <input name="ref" placeholder="where you keep it" size="24" required aria-label="where you keep it"> <input name="component" placeholder="for what" size="10" aria-label="for what"> <button class="sm">Save</button></form><p class="limits">Only the reference is stored; the file stays where you keep it.</p></details>'''}</div></div>
<p class="limits" style="margin-top:1rem"><a href="/house/{hid}/history">Full history and change log</a> · <a href="/house/{hid}/export.json">Download the whole record</a></p>
</section>"""
    return page(f"{_addr(p)} — HomeKeeper", body, snapshot=snapshot)


# ---------------------------------------------------------------- house section with inline edit
EDITABLE = {n for n, *_ in questions.ONBOARDING} | {"year_built", "basement", "roof_type", "exterior_finish", "stories", "fireplaces"}


def _edit_form(p: Profile, name: str) -> str:
    kind = next((k for n, _, _, k in questions.ONBOARDING if n == name), "text")
    hint = next((h for n, _, h, _ in questions.ONBOARDING if n == name), "")
    if name in ("year_built", "fireplaces", "stories"):
        kind, hint = "number", ""
    if kind == "bool":
        inp = '<select name="value"><option value="yes">Yes</option><option value="no">No</option><option value="unknown">Don\'t know</option></select>'
    elif kind == "choice":
        inp = '<select name="value">' + "".join(f'<option value="{e(o.strip())}">{e(o.strip())}</option>' for o in hint.split("/")) + '<option value="unknown">Don\'t know</option></select>'
    elif kind == "year":
        inp = '<input name="value" placeholder="year" size="6" inputmode="numeric">'
    elif kind == "date":
        inp = '<input type="date" name="value">'
    else:
        inp = f'<input name="value" placeholder="{e(hint)}" size="16">'
    return (f'<details class="ed"><summary>edit</summary><form method="post" action="/house/{e(p.house_id)}/answer"><input type="hidden" name="field" value="{e(name)}"><input type="hidden" name="next" value="house">'
            f'{inp} <input name="reason" placeholder="source (invoice, report page)" size="20" aria-label="source"> <button class="sm">Save</button></form></details>')


def _rows_edit(p: Profile, spec, *, area=False, norm=None, snapshot=False) -> str:
    out = []
    for name, label in spec:
        f = p.get(name)
        if f.is_unknown:
            val = '<span class="unknown">unknown</span>' + (f' <span class="limits">{e(f.note)}</span>' if f.note and area else "")
        else:
            val = e(_area_text(name, f.value) if area else fmt(f.value)) + (f" {e(f.units)}" if f.units and not area else "")
        tg = "" if (norm and f.evidence_type == norm and f.verification_status == "unverified") or f.is_unknown else tag(f)
        hist = f'<div class="limits">was {e(f.history[-1].get("value"))}</div>' if f.history else ""
        lim = f'<div class="limits">{e(f.limitations)}</div>' if area and f.limitations and not f.is_unknown else ""
        ed = _edit_form(p, name) if (name in EDITABLE and not snapshot and not area) else ""
        out.append(f"<tr><td>{e(label)}</td><td>{val} {tg} {ed}{hist}{lim}</td></tr>")
    return f'<table class="fields">{"".join(out)}</table>'


def _house_section(p: Profile, snapshot: bool) -> str:
    hid = e(p.house_id)
    eq = "".join(f"<tr><td>{e(x['component'].replace('_', ' '))}</td><td>{e(x.get('make',''))} {e(x.get('model',''))} · installed {e(x.get('installed_year') or '?')}"
                 f"{(' · last service ' + e(x['last_service_date'])) if x.get('last_service_date') else ''}{' · manual on file' if x.get('manual_source_id') else ''}"
                 f"{' <span class=tag>replaced</span>' if x['status'] != 'installed' else ''}</td></tr>" for x in p.equipment)
    fn = "".join(f"<tr><td>{e(x['component'])}</td><td>{e(x['description'])} <span class='tag'>{e(x['severity'])}</span>{' <span class=tag>resolved</span>' if x['status'] == 'resolved' else ''} <span class='limits'>{e(x['source_doc'])}</span></td></tr>" for x in p.findings)
    rs = "".join(f"<tr><td>{e(k.replace('_', ' '))}</td><td>{e(v)}</td></tr>" for k, v in p.responsibilities.items())
    forms = "" if snapshot else f"""<details class="group"><summary>Add equipment</summary>
<form method="post" action="/house/{hid}/equipment" class="row"><select name="component" aria-label="what"><option value="furnace">furnace</option><option value="ac">air conditioner</option><option value="water_heater">water heater</option><option value="sump_pump">sump pump</option><option value="roof">roof</option></select>
<input name="make" placeholder="make" size="10" aria-label="make"> <input name="model" placeholder="model" size="10" aria-label="model"> <input name="year" placeholder="year installed" size="12" inputmode="numeric" aria-label="year installed">
<select name="manual" aria-label="manual"><option value="">manual: not on file</option><option value="goodman_rs6612023">Goodman furnace manual</option><option value="carrier_58d_u_9sm">Carrier furnace manual</option><option value="bradford_white_io">Bradford White water heater manual</option><option value="aosmith_100398943">A. O. Smith water heater manual</option><option value="zoeller_fm2676">Zoeller sump pump manual</option><option value="liberty_7035000">Liberty sump pump manual</option></select>
<button class="sm">Save</button></form><p class="limits">A replacement retires the old unit and resets its planning window. A manual on file sets the maintenance interval.</p></details>
<details class="group"><summary>Add a finding from the inspection report</summary>
<form method="post" action="/house/{hid}/finding" class="row"><input name="component" placeholder="what (roof, electrical…)" size="16" required aria-label="what">
<select name="severity" aria-label="how serious"><option>safety</option><option>major</option><option>minor</option><option>info</option></select>
<input name="description" placeholder="what the report says" size="32" required aria-label="what the report says"> <input name="source" placeholder="report page" size="10" aria-label="report page"> <input type="date" name="date" aria-label="date observed"> <button class="sm">Save</button></form></details>
<details class="group"><summary>Someone else is responsible for part of the house</summary>
<form method="post" action="/house/{hid}/responsibility" class="row"><input name="component" placeholder="what (roof, gutters…)" size="14" required aria-label="what"> <input name="party" placeholder="who (HOA, landlord)" size="18" required aria-label="who"> <input name="reason" placeholder="why" size="18" aria-label="why"> <button class="sm">Save</button></form></details>"""
    purge = "" if snapshot else ('<p class="row" style="margin-top:.8rem"><form class="inline" method="post" action="/house/' + hid + '/purge" '
                                 'onsubmit="return confirm(\'Remove documents, completions, findings, estimates and your answers from this record?\')">'
                                 '<button class="sm quiet">Remove private information</button></form></p>')
    return f"""<p class="sect-note">Facts from the county assessor are unmarked; yours are marked <span class="tag own">owner</span>; inspection findings <span class="tag pro">inspection</span>. Dotted underlines are gaps. Edit anything that's wrong — the plan above updates.</p>
<h3>About the house</h3>{_rows_edit(p, ABOUT, norm="public_record", snapshot=snapshot)}
<h3>Systems</h3>{_rows_edit(p, SYSTEMS, snapshot=snapshot)}
<h3>Equipment</h3><table class="fields">{eq or '<tr><td colspan=2 class=empty>none recorded</td></tr>'}</table>
<h3>Findings from the inspection</h3><table class="fields">{fn or '<tr><td colspan=2 class=empty>none recorded</td></tr>'}</table>
<h3>Who is responsible</h3><table class="fields">{rs or '<tr><td colspan=2 class=empty>you, for everything recorded</td></tr>'}</table>
{forms}
<h3>The area <span class="limits">describes the neighbourhood, not this house</span></h3>{_rows_edit(p, AREA, area=True, norm="regional_exposure", snapshot=snapshot)}
<details class="group"><summary>Details and administration</summary>{_rows_edit(p, DETAILS, snapshot=snapshot)}
{purge}</details>"""
