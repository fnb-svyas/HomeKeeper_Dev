"""Simplified pages for the local app: landing, Today, Tasks, House, Money, History.

Principles: one primary action per screen; the next three are the page; supporting detail is one
click away; plain words for every label; counts instead of lists for anything not needed now.
Reuses the CSS, tags and task blocks from hk.web.
"""
from __future__ import annotations

import datetime as _dt
import html

from . import actions, budget, questions, reminders, reports, rules
from .evidence import Profile
from .web import CSS, EV_TAG, e, fmt, page as _page, tag, task_block, _priority_line

EXTRA_CSS = """
.hero{padding:2.5rem 0 1.5rem;max-width:40rem}
.next>li{max-width:52rem}
.hero h1{font-size:2.4rem;margin:0 0 .6rem}
.hero p{font-size:1.1rem;color:var(--ink-2);margin:0 0 1.4rem}
.addr{display:flex;gap:.5rem;flex-wrap:wrap}.addr input{flex:1 1 20rem;font-size:1.05rem;padding:.55rem .7rem}
.addr button{font-size:1rem;padding:.55rem 1rem}
.houses{list-style:none;padding:0;margin:0}.houses li{padding:.7rem 0;border-top:1px solid var(--mortar)}
.houses a{text-decoration:none;font-size:1.15rem}.houses .meta{display:block}
.strip{display:flex;gap:1.5rem;flex-wrap:wrap;font-size:.9rem;color:var(--ink-2);margin:0 0 1.5rem;padding-bottom:1rem;border-bottom:1px solid var(--mortar)}
.strip b{color:var(--ink);font-weight:500}
.done-btn{margin-top:.4rem}
.next .act{grid-column:2;margin-top:.5rem}
.sect{margin:1.6rem 0}.sect h2{margin:0 0 .5rem}
.ask{border-top:2px solid var(--ink);padding-top:.8rem;margin-top:2rem}
.ask .q{border-top:0;padding:.4rem 0}
.more{font-size:.9rem;color:var(--ink-2)}
.group summary{font-size:1.05rem;color:var(--ink);font-family:inherit}
.group summary .n{color:var(--ink-2);font-size:.9rem}
.onb{max-width:42rem}.onb .q{padding:.9rem 0}
.center{max-width:46rem;margin:0 auto}
.money h2 .limits{display:block;margin-top:.1rem}
.quiet-link{color:var(--ink-2);font-size:.9rem}
"""


def page(title, body, *, nav=(), snapshot=False):
    return _page(title, body, nav=nav, snapshot=snapshot).replace("</style>", EXTRA_CSS + "</style>", 1)


def nav_for(p: Profile, cur: str):
    h = f"/house/{p.house_id}"
    return [(h, "Today", cur == "today"), (f"{h}/tasks", "Tasks", cur == "tasks"), (f"{h}/house", "House", cur == "house"),
            (f"{h}/money", "Money", cur == "money"), (f"{h}/history", "History", cur == "history")]


def _addr(p: Profile) -> str:
    a = p.value("matched_address") or p.address_input
    return _title(a)


def _title(a: str) -> str:
    out = []
    for w_ in str(a).split():
        if w_.isdigit() or (len(w_) <= 3 and w_.upper() in ("PA", "NE", "NW", "SE", "SW", "N", "S", "E", "W")):
            out.append(w_.upper() if not w_.isdigit() else w_)
        else:
            out.append(w_.capitalize())
    return " ".join(out)


def _plain_why(t: rules.Task) -> str:
    if t.status == "finding":
        return "Your inspector documented this. " + (t.why.replace("Documented in", "See") if t.why else "")
    if t.refined_by and "—" in t.refined_by:
        return t.why.split(" Refined by")[0] + " Your unit's own manual sets the interval."
    return t.why


def _summary(p: Profile) -> str:
    bits = []
    yb = p.value("year_built"); bits.append(f"Built <b>{e(yb)}</b>" if yb else "Year built <span class=unknown>unknown</span>")
    b = p.value("basement"); bits.append(f"<b>{e(b)}</b> basement" if b else "Basement <span class=unknown>unknown</span>")
    m = p.value("municipality"); bits.append(f"<b>{e(m)}</b>" if m else "Municipality <span class=unknown>unknown</span>")
    st = p.value("stage"); bits.append("Under contract" + (f" · closing <b>{e(p.value('closing_date'))}</b>" if p.value("closing_date") else "") if st == "under_contract" else "Owner")
    return f'<div class="strip">{"".join(f"<span>{x}</span>" for x in bits)}</div>'


# ---------------------------------------------------------------- landing
def landing(ids: list[str], msg: str = "") -> str:
    items = []
    for i in ids:
        try:
            p = Profile.load(i)
        except Exception:
            continue
        if p.value("stage") == "before_buy":
            continue  # looked up in Browse Homes, not owned
        live = rules.prioritize(rules.evaluate(p))
        first = live[0].title if live else "nothing open"
        syn = ' <span class="tag">demo</span>' if p.synthetic else ""
        items.append(f'<li><a href="/house/{e(i)}">{e(_addr(p))}</a>{syn}<span class="meta">Next: {e(first)}</span></li>')
    houses = f'<h2>Your houses</h2><ul class="houses">{"".join(items)}</ul>' if items else ""
    body = f"""<div class="center">{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<div class="hero"><h1>Know what your house needs next.</h1>
<p>Enter an address in Allegheny County. HomeKeeper pulls the public record and the area's known risks, then asks only the few questions that change what you should do first.</p>
<form method="post" action="/build" class="addr" onsubmit="var b=this.querySelector('button');b.disabled=true;b.textContent='Looking up the record…';"><input name="address" placeholder="123 Main St, Pittsburgh, PA 15228" aria-label="Address" required autofocus><button class="primary">Start</button></form>
<p class="limits">Takes a few seconds. Nothing is sent anywhere except the public data services that answer the lookup. This is not an inspection.</p></div>
{houses}
<p class="more" style="margin-top:2rem"><a href="/">Back</a> · <a href="/browse">Looking at a home to buy instead?</a></p>
<p class="more">Want to look first? <form class="inline" method="post" action="/sample"><input type="hidden" name="name" value="complete"><button class="quiet">Open the demo house</button></form> <span class="limits">(invented 1928 brick colonial; marked as a demo everywhere)</span></p>
</div>"""
    return page("HomeKeeper", body, nav=[("/", "Houses", True)]) if False else page("HomeKeeper", body, nav=[])


# ---------------------------------------------------------------- onboarding (after build)
ONBOARD_FIELDS = ["owner_confirms_match", "stage", "closing_date", "heating_fuel", "heating_type", "water_heater_installed_year",
                  "roof_installed_year", "sump_pump_present"]


def onboarding(p: Profile, msg: str = "") -> str:
    tasks = rules.evaluate(p)
    qs = [q for q in questions.pending(p, tasks) if q["field"] in ONBOARD_FIELDS]
    order = {f: i for i, f in enumerate(ONBOARD_FIELDS)}
    qs.sort(key=lambda q: order.get(q["field"], 99))
    m = p.match
    match_html = ""
    if m.get("ambiguous") or m.get("chosen") is None:
        cands = "".join(f'<li>{e(c["address"])} — parcel {e(c.get("parcel_id") or "—")} '
                        f'<form class="inline" method="post" action="/house/{e(p.house_id)}/choose"><input type="hidden" name="choose" value="{i}"><button>This one</button></form></li>'
                        for i, c in enumerate(m.get("candidates", [])))
        match_html = f'<div class="notice"><b>Which address did you mean?</b> {e(m.get("reason"))}<ul>{cands}</ul></div>'
        qs = [q for q in qs if q["field"] != "owner_confirms_match"]
    elif not m.get("owner_confirmed"):
        c = m["candidates"][m["chosen"]]
        match_html = (f'<div class="q"><label>Is this the right house? <b>{e(c["address"])}</b></label>'
                      f'<div class="row"><form class="inline" method="post" action="/house/{e(p.house_id)}/answer"><input type="hidden" name="field" value="owner_confirms_match"><input type="hidden" name="value" value="yes"><input type="hidden" name="next" value="onboard"><button class="primary">Yes</button></form> '
                      f'<a class="btn quiet" href="/owner">No, try another address</a></div></div>')
        qs = [q for q in qs if q["field"] != "owner_confirms_match"]
    else:
        qs = [q for q in qs if q["field"] != "owner_confirms_match"]
    qh = "".join(_question(p, q, next_="onboard") for q in qs[:6])
    if not qh and not match_html:
        qh = '<p class="gap">Nothing left to ask right now.</p>'
    body = f"""<div class="onb">{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>A few questions about the house</h1>
<p>{e(_addr(p))}. Each answer changes what you'll be asked to do first. Skip anything you don't know — it stays marked unknown, never guessed.</p>
{match_html}{qh}
<p class="row" style="margin-top:1.5rem"><a class="btn primary" href="/house/{e(p.house_id)}">Show my plan</a> <span class="limits">You can answer the rest later from the Today page.</span></p></div>"""
    return page("A few questions", body, nav=nav_for(p, "today"))


def _question(p: Profile, q: dict, *, next_: str = "today") -> str:
    kind = q["type"]
    if kind == "bool":
        inp = ('<select name="value"><option value="">—</option><option value="yes">Yes</option><option value="no">No</option>'
               '<option value="unknown">Don\'t know</option></select>')
    elif kind == "choice":
        opts = [o.strip() for o in q["answer"].split("/")]
        inp = '<select name="value"><option value="">—</option>' + "".join(f'<option value="{e(o)}">{e(o)}</option>' for o in opts) + '<option value="unknown">Don\'t know</option></select>'
    elif kind == "year":
        inp = '<input name="value" placeholder="year" size="6" inputmode="numeric">'
    elif kind == "date":
        inp = '<input type="date" name="value">'
    else:
        inp = f'<input name="value" placeholder="{e(q["answer"])}" size="24">'
    return f"""<div class="q"><form method="post" action="/house/{e(p.house_id)}/answer"><input type="hidden" name="field" value="{e(q['field'])}"><input type="hidden" name="next" value="{e(next_)}">
<label>{e(q['question'])}<br><span class="because">{e(q['matters_because'])}</span></label>
<div class="row">{inp} <button class="quiet">Save</button></div></form></div>"""


# ---------------------------------------------------------------- today
def today(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    live = rules.prioritize(tasks)
    top = live[:3]
    hid = e(p.house_id)
    items = []
    for t in top:
        act = "" if snapshot else f"""<div class="act row"><form class="inline" method="post" action="/house/{hid}/done"><input type="hidden" name="task" value="{e(t.rule_id)}"><input type="hidden" name="next" value="today"><button class="primary">Done</button></form>
<a class="quiet-link" href="/house/{hid}/tasks#{e(t.rule_id)}">Details, snooze or other options</a></div>"""
        items.append(f'<li><p class="title">{e(t.title)}</p><p class="why">{e(_plain_why(t))}</p><p class="meta">{e(_priority_line(t))}</p>{act}</li>')
    qs = questions.pending(p, tasks)
    ask = "".join(_question(p, q) for q in qs[:2])
    more_q = f' <a class="quiet-link" href="/house/{hid}/tasks#questions">{len(qs) - 2} more</a>' if len(qs) > 2 else ""
    remaining = max(0, len(live) - 3)
    buy = (f'<p class="more">Under contract? <a href="/house/{hid}/report/buy">Read the before-you-buy summary</a> — what is known, what is not, and the deadlines.</p>'
           if p.value("stage") == "under_contract" else "")
    body = f"""{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>{e(_addr(p))}</h1>{_summary(p)}
<h2 style="margin-top:0">Do these first</h2>
<ol class="next">{"".join(items) or '<li><p class="title gap">Nothing open. Nice.</p></li>'}</ol>
<p class="more">{f'<a href="/house/{hid}/tasks">{remaining} more tasks</a> · ' if remaining else ''}<a href="/house/{hid}/fit">I have limited time and money</a> · <a href="/house/{hid}/reminders.ics">Put these in my calendar</a></p>
{buy}
{f'<div class="ask"><h2>One thing that would sharpen this plan</h2>{ask}<p class="limits">Answering changes the list above.{more_q}</p></div>' if ask else ''}"""
    return page(f"{_addr(p)} — today", body, nav=nav_for(p, "today"), snapshot=snapshot)


# ---------------------------------------------------------------- tasks
def tasks_page(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    live = rules.prioritize(tasks)
    hid = e(p.house_id)
    def blocks(items):
        return "".join(f'<div id="{e(t.rule_id)}">{task_block(p, t, actions_on=not snapshot)}</div>' for t in items)
    now = [t for t in live if t.status in ("finding", "applies") and not t.due.startswith("next due")]
    later = [t for t in live if t.status == "applies" and t.due.startswith("next due")]
    check = [t for t in live if t.status == "verification"]
    answer = [t for t in live if t.status == "needs_info"]
    hidden = {"snoozed": "Snoozed", "dismissed": "Marked does-not-apply", "done": "Done", "someone_else": "Someone else's responsibility",
              "excluded": "Not applicable to this house", "not_applicable": "Waiting on data"}
    hid_sections = ""
    for st, label in hidden.items():
        items = [t for t in tasks if t.status == st]
        if items:
            hid_sections += f'<details class="group"><summary>{e(label)} <span class="n">({len(items)})</span></summary>{blocks(items)}</details>'
    qs = questions.pending(p, tasks)
    qh = "".join(_question(p, q, next_="tasks") for q in qs)
    body = f"""{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>All tasks</h1>{_summary(p)}
<div class="sect"><h2>Do now <span class="limits">({len(now)})</span></h2>{blocks(now) or '<p class="gap">nothing due right now</p>'}</div>
<div class="sect"><h2>Check first <span class="limits">({len(check)})</span></h2><p class="limits">Something about the house is unknown; these tell you how to find out.</p>{blocks(check) or '<p class="gap">nothing to verify</p>'}</div>
<div class="sect"><h2>Answer first <span class="limits">({len(answer)})</span></h2>{blocks(answer) or '<p class="gap">nothing waiting on an answer</p>'}</div>
<div class="sect"><h2>Later <span class="limits">({len(later)})</span></h2><p class="limits">Recurring work already done once; shown with its next date.</p>{blocks(later) or '<p class="gap">none yet</p>'}</div>
<div class="sect" id="questions"><h2>Questions <span class="limits">({len(qs)})</span></h2>{qh or '<p class="gap">none open</p>'}</div>
<div class="sect"><h2>Not shown above</h2>{hid_sections or '<p class="gap">nothing hidden</p>'}</div>"""
    return page(f"{_addr(p)} — tasks", body, nav=nav_for(p, "tasks"), snapshot=snapshot)


# ---------------------------------------------------------------- house
ABOUT = [("year_built", "Year built"), ("style", "Style"), ("stories", "Stories"), ("basement", "Basement"), ("exterior_finish", "Exterior"),
         ("roof_type", "Roof"), ("living_area", "Living area"), ("lot_area", "Lot"), ("bedrooms", "Bedrooms"), ("full_baths", "Full baths"),
         ("fireplaces", "Fireplaces"), ("condition_assessor", "Assessor's condition"), ("grade_assessor", "Assessor's grade")]
SYSTEMS = [("heating_cooling", "Heating / cooling (record)"), ("heating_fuel", "Heating fuel"), ("heating_type", "Heating type"), ("ac_present", "Central AC"),
           ("furnace_installed_year", "Furnace installed"), ("water_heater_type", "Water heater"), ("water_heater_installed_year", "Water heater installed"),
           ("roof_installed_year", "Roof installed"), ("sump_pump_present", "Sump pump"), ("sump_pump_installed_year", "Sump pump installed"),
           ("wiring_type", "Wiring"), ("plumbing_supply_material", "Supply pipes"), ("radon_result_pci_l", "Radon result (pCi/L)"), ("radon_result_date", "Radon tested"),
           ("radon_mitigation_present", "Radon system"), ("chimney_in_use", "Chimney in use"), ("dryer_present", "Dryer"), ("exterior_hose_bibs", "Outside faucets"), ("gutters_present", "Gutters")]
AREA = [("radon_zip_stats", "Radon in this ZIP"), ("flood_zone", "Flood zone"), ("undermined", "Mining under or near"), ("landslide_prone", "Landslide-prone area"),
        ("soil_map_unit", "Soil"), ("climate_normals", "Climate"), ("point_of_sale_sewer_rule", "Sewer test at sale")]
DETAILS = [("matched_address", "Matched address"), ("coordinates", "Coordinates"), ("parcel_id", "Parcel"), ("municipality", "Municipality"),
           ("school_district", "School district"), ("use_description", "Use"), ("last_sale_date", "Last sale"), ("city_permits_since_2019", "City permits since 2019"),
           ("stage", "Stage"), ("closing_date", "Closing date")]


def _area_text(name: str, v) -> str:
    if name == "radon_zip_stats" and isinstance(v, dict):
        return f"{v['tests']} tests on file; median {v['median_pci_l']} pCi/L; {v['pct_at_or_above_4']}% at or above 4 (through {v.get('latest_test') or '?'})"
    if name == "flood_zone" and isinstance(v, dict):
        return f"Zone {v.get('fld_zone') or '—'}" + (" — in a Special Flood Hazard Area" if v.get("sfha") else " — outside the special hazard area" if v.get("sfha") is False else "")
    if name in ("undermined", "landslide_prone"):
        return "yes (mapped)" if v else "not mapped here"
    if name == "soil_map_unit" and isinstance(v, dict):
        return f"{v.get('muname') or '—'}; drainage: {v.get('drainagecl') or '?'}; frost action: {v.get('frostact') or '?'}"
    if name == "climate_normals" and isinstance(v, dict):
        return f"median first freeze {v.get('first_freeze_median')}, last {v.get('last_freeze_median')}; {v.get('annual_snow_in')} in snow/yr"
    if name == "point_of_sale_sewer_rule" and isinstance(v, dict):
        return (f"{v['name']}: required ({v['applies']}); fee {v['fee']}; lead time {v['lead_time']}; valid {v['validity']}" if v.get("known")
                else "not compiled for this municipality — ask the municipality")
    return fmt(v)


def _rows(p: Profile, spec, *, area=False, norm: str | None = None) -> str:
    """norm: an evidence_type whose tag is implied by the section heading and therefore not repeated per row."""
    out = []
    for name, label in spec:
        f = p.get(name)
        if f.is_unknown:
            val = '<span class="unknown">unknown</span>' + (f' <span class="limits">{e(f.note)}</span>' if f.note and area else "")
        else:
            val = e(_area_text(name, f.value) if area else fmt(f.value)) + (f" {e(f.units)}" if f.units and not area else "")
        extra = ""
        if f.history:
            extra = f'<div class="limits">was {e(f.history[-1].get("value"))} ({e(EV_TAG.get(f.history[-1].get("evidence_type", ""), ("?", ""))[0])})</div>'
        lim = f'<div class="limits">{e(f.limitations)}</div>' if area and f.limitations and not f.is_unknown else ""
        tg = "" if (norm and f.evidence_type == norm and f.verification_status == "unverified") or f.is_unknown else tag(f)
        out.append(f"<tr><td>{e(label)}</td><td>{val} {tg}{extra}{lim}</td></tr>")
    return f'<table class="fields">{"".join(out)}</table>'


def house_page(p: Profile, msg: str = "") -> str:
    hid = e(p.house_id)
    eq = "".join(f"<tr><td>{e(x['component'].replace('_', ' '))}</td><td>{e(x.get('make',''))} {e(x.get('model',''))} · installed {e(x.get('installed_year') or '?')}"
                 f"{' · manual on file' if x.get('manual_source_id') else ''} <span class='tag'>{e(x['status'])}</span></td></tr>" for x in p.equipment)
    fn = "".join(f"<tr><td>{e(x['component'])}</td><td>{e(x['description'])} <span class='tag'>{e(x['severity'])}</span><span class='tag'>{e(x['status'])}</span> <span class='limits'>{e(x['source_doc'])}</span></td></tr>" for x in p.findings)
    rs = "".join(f"<tr><td>{e(k.replace('_', ' '))}</td><td>{e(v)}</td></tr>" for k, v in p.responsibilities.items())
    forms = f"""<details class="group"><summary>Add equipment</summary>
<form method="post" action="/house/{hid}/equipment" class="row"><select name="component"><option>furnace</option><option>ac</option><option>water_heater</option><option>sump_pump</option><option>roof</option></select>
<input name="make" placeholder="make" size="10"> <input name="model" placeholder="model" size="10"> <input name="year" placeholder="year installed" size="12" inputmode="numeric">
<select name="manual"><option value="">manual: none on file</option><option>goodman_rs6612023</option><option>carrier_58d_u_9sm</option><option>bradford_white_io</option><option>aosmith_100398943</option><option>zoeller_fm2676</option><option>liberty_7035000</option></select>
<button>Save</button></form><p class="limits">A replacement retires the old unit and resets its planning window.</p></details>
<details class="group"><summary>Add a finding from the inspection report</summary>
<form method="post" action="/house/{hid}/finding" class="row"><input name="component" placeholder="what (roof, electrical…)" size="16" required>
<select name="severity"><option>safety</option><option>major</option><option>minor</option><option>info</option></select>
<input name="description" placeholder="what the report says" size="32" required> <input name="source" placeholder="report page" size="10"> <input type="date" name="date" aria-label="date"> <button>Save</button></form></details>
<details class="group"><summary>Someone else is responsible for part of the house</summary>
<form method="post" action="/house/{hid}/responsibility" class="row"><input name="component" placeholder="what (roof, gutters…)" size="14" required> <input name="party" placeholder="who (HOA, landlord)" size="18" required> <input name="reason" placeholder="why" size="18"> <button>Save</button></form></details>"""
    body = f"""{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>{e(_addr(p))}</h1>{_summary(p)}
<p class="limits">Facts you entered are marked <span class="tag own">owner</span>; inspection findings <span class="tag pro">inspection</span>. The assessor's record is a valuation snapshot, not an inspection. Dotted underlines are gaps you can fill on the Tasks page.</p>
<div class="sect"><h2>About the house <span class="limits">from the county assessor's record unless marked</span></h2>{_rows(p, ABOUT, norm="public_record")}</div>
<div class="sect"><h2>Systems</h2>{_rows(p, SYSTEMS)}</div>
<div class="sect"><h2>Equipment</h2><table class="fields">{eq or '<tr><td colspan=2 class=gap>none recorded</td></tr>'}</table></div>
<div class="sect"><h2>Findings from the inspection</h2><table class="fields">{fn or '<tr><td colspan=2 class=gap>none recorded</td></tr>'}</table></div>
<div class="sect"><h2>Who is responsible</h2><table class="fields">{rs or '<tr><td colspan=2 class=gap>you, for everything recorded</td></tr>'}</table></div>
<div class="sect">{forms}</div>
<div class="sect"><h2>The area <span class="limits">describes the neighbourhood, not this house</span></h2>{_rows(p, AREA, area=True, norm="regional_exposure")}</div>
<details class="group"><summary>Details and administration</summary>{_rows(p, DETAILS)}
<p class="row" style="margin-top:1rem"><a class="btn quiet" href="/house/{hid}/export.json">Download the whole record</a> <form class="inline" method="post" action="/house/{hid}/purge" onsubmit="return confirm('Remove documents, completions, findings, estimates and your answers from this record?')"><button class="quiet">Remove private information</button></form></p></details>"""
    return page(f"{_addr(p)} — house", body, nav=nav_for(p, "house"))


# ---------------------------------------------------------------- money
def money_page(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    b = budget.build_budgets(p, tasks)
    def money(x): return f"${x:,.0f}"
    t = b["totals"]
    def rows(items, kind):
        out = []
        for i in items:
            if kind == "routine":
                rng = "your time only" if i["basis"] == "none" else f"{money(i['low'])}–{money(i['high'])} a year"
                out.append(f"<tr><td>{e(i['task'])}</td><td>{rng}</td><td class='limits'>{e(i['basis'].replace('_',' '))} · {e(i['source'])}</td></tr>")
            elif kind == "repairs":
                out.append(f"<tr><td>{e(i['task'])}<div class='limits'>{e(i['scope'])}{(' · excludes ' + e(i['exclusions'])) if i['exclusions'] else ''}</div></td><td>{money(i['low'])}–{money(i['high'])}</td><td class='limits'>{e(i['basis'].replace('_',' '))} · {e(i['source'])} {e(i['date'])}</td></tr>")
            else:
                out.append(f"<tr><td>{e(i['component'].replace('_',' '))}{('<div class=limits>' + e(i['overlap_note']) + '</div>') if i.get('overlap_note') else ''}</td><td>{money(i['monthly_low'])}–{money(i['monthly_high'])} a month<div class='limits'>{money(i['low'])}–{money(i['high'])} over {i['years']} years</div></td><td class='limits'>{e(i['basis'].replace('_',' '))}</td></tr>")
        return "".join(out)
    un = "".join(f"<tr><td>{e(u['task'])}</td><td class='limits'>{e(u['why'])}</td></tr>" for u in b["unknown"])
    hid = e(p.house_id)
    forms = "" if snapshot else f"""<details class="group"><summary>Add a quote or price reference</summary>
<form method="post" action="/house/{hid}/quote" class="row"><input name="applies_to" placeholder="task id or component" size="18" required> <input name="low" placeholder="low $" size="7" required> <input name="high" placeholder="high $" size="7" required>
<select name="basis"><option value="user_quote">a quote I received</option><option value="published_reference">a published reference</option><option value="planning_assumption">my planning guess</option></select> <input name="scope" placeholder="what it covers" size="22" required> <input name="exclusions" placeholder="what it excludes" size="14"> <input name="source" placeholder="who / where" size="14"> <button>Save</button></form></details>
<details class="group"><summary>Set aside for a future replacement</summary>
<form method="post" action="/house/{hid}/reserve" class="row"><input name="component" placeholder="what (roof, furnace…)" size="14" required> <input name="years" placeholder="over how many years" size="16" required> <input name="low" placeholder="low $" size="7" required> <input name="high" placeholder="high $" size="7" required>
<select name="basis"><option value="planning_assumption">my planning guess</option><option value="user_quote">a quote I received</option><option value="published_reference">a published reference</option></select> <button>Save</button></form>
<p class="limits">Average service life is not a failure date; you choose the period.</p></details>"""
    body = f"""{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>Money</h1>{_summary(p)}
<p class="limits">Only prices you entered or references you chose are added up. Nothing is estimated for you.</p>
<div class="sect money"><h2>Routine upkeep <span class="limits">{money(t['routine_per_year'][0])}–{money(t['routine_per_year'][1])} a year, plus your time</span></h2>
<div class="tbl"><table class="b">{rows(b['routine'], 'routine') or '<tr><td class=gap>nothing priced yet</td></tr>'}</table></div></div>
<div class="sect money"><h2>Known repairs <span class="limits">{money(t['repairs'][0])}–{money(t['repairs'][1])}</span></h2>
<div class="tbl"><table class="b">{rows(b['repairs'], 'repairs') or '<tr><td class=gap>no quotes yet — the inspection findings are the list to price</td></tr>'}</table></div></div>
<div class="sect money"><h2>Saving for replacements <span class="limits">{money(t['replacement_reserve_per_month'][0])}–{money(t['replacement_reserve_per_month'][1])} a month</span></h2>
<div class="tbl"><table class="b">{rows(b['replacements'], 'replacements') or '<tr><td class=gap>no scenarios yet</td></tr>'}</table></div></div>
{f'<details class="group"><summary>Not priced yet <span class="n">({len(b["unknown"])})</span></summary><div class="tbl"><table class="b">{un}</table></div></details>' if un else ''}
<div class="sect">{forms}</div>"""
    return page(f"{_addr(p)} — money", body, nav=nav_for(p, "money"), snapshot=snapshot)


# ---------------------------------------------------------------- history
def history_page(p: Profile, msg: str = "", *, snapshot: bool = False) -> str:
    hid = e(p.house_id)
    comps = sorted(getattr(p, "completions", []) or [], key=lambda c: c["date"], reverse=True)
    spend = sum(float(c["cost"]) for c in comps if c.get("cost"))
    rows = "".join(f"<tr><td>{e(c['date'])}</td><td>{e(next((t['title'] for t in rules.load_rules() if t['id']==c['rule_id']), c['rule_id']))}<div class='limits'>{e(c.get('notes',''))}</div></td><td>{('$%s' % format(c['cost'], ',.0f')) if c.get('cost') is not None else '—'}</td><td>{e(c.get('contractor') or 'you')}</td></tr>" for c in comps)
    docs = "".join(f"<tr><td>{e(d['kind'])}</td><td>{e(d['title'])}</td><td class='limits'>{e(d['ref'])}</td></tr>" for d in (getattr(p, 'documents', []) or []))
    eq = "".join(f"<tr><td>{e(x['component'].replace('_',' '))}</td><td>{e(x.get('make',''))} {e(x.get('model',''))} · installed {e(x.get('installed_year') or '?')} · last service {e(x.get('last_service_date') or '—')} <span class='tag'>{e(x['status'])}</span></td></tr>" for x in p.equipment)
    body = f"""{f'<p class="notice">{e(msg)}</p>' if msg else ''}
<h1>History</h1>{_summary(p)}
<div class="sect"><h2>Work done <span class="limits">{len(comps)} items · ${spend:,.0f} recorded</span></h2>
<div class="tbl"><table class="b">{rows or '<tr><td class=gap>nothing recorded yet — mark a task done from Today</td></tr>'}</table></div></div>
<div class="sect"><h2>Equipment</h2><div class="tbl"><table class="b">{eq or '<tr><td class=gap>none recorded</td></tr>'}</table></div></div>
<div class="sect"><h2>Documents</h2><div class="tbl"><table class="b">{docs or '<tr><td class=gap>none — invoices, manuals, warranties and photos go here as references</td></tr>'}</table></div>
{'' if snapshot else f'''<details class="group"><summary>Add a document reference</summary><form method="post" action="/house/{hid}/document" class="row"><select name="kind"><option>invoice</option><option>manual</option><option>warranty</option><option>photo</option><option>report</option><option>permit</option><option>other</option></select>
<input name="title" placeholder="title" size="24" required> <input name="ref" placeholder="where you keep it" size="30" required> <input name="component" placeholder="for what" size="12"> <button>Save</button></form><p class="limits">Only the reference is stored; the file stays where you keep it.</p></details>'''}</div>
<div class="sect"><h2>Reminders</h2><p><a class="btn" href="/house/{hid}/reminders.ics">Download the calendar file</a> <span class="limits">Import it into Outlook, Google or Apple Calendar. It is a snapshot; download again after you record work. Nothing runs in the background and nothing emails you.</span></p>
<details class="group"><summary>Next 90 days</summary><pre class="doc">{e(reminders.render_upcoming(p, 90))}</pre></details></div>
<details class="group"><summary>Full change log</summary><pre class="doc">{e(actions.history(p))}</pre></details>"""
    return page(f"{_addr(p)} — history", body, nav=nav_for(p, "history"), snapshot=snapshot)


def report_page(p: Profile, kind: str, *, snapshot: bool = False) -> str:
    tasks = rules.evaluate(p)
    fn = {"buy": reports.before_you_buy, "plan90": reports.first_90_days, "calendar": reports.calendar}.get(kind, reports.before_you_buy)
    titles = {"buy": "Before you buy", "plan90": "Your first 90 days", "calendar": "Twelve-month calendar"}
    hid = e(p.house_id)
    links = " · ".join(f'<a href="/house/{hid}/report/{k}">{e(v)}</a>' for k, v in titles.items() if k != kind)
    body = f"""<h1>{e(titles.get(kind, 'Report'))}</h1>{_summary(p)}<p class="more">Also: {links}</p><pre class="doc">{e(fn(p, tasks))}</pre>"""
    return page(f"{_addr(p)} — {titles.get(kind, 'report')}", body, nav=nav_for(p, "today"), snapshot=snapshot)

