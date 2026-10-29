"""Rendering of the Ownership Score panel for Browse Homes (dusk theme; see browse.CSS + SCORE_CSS)."""
from __future__ import annotations

import html

from . import score
from .evidence import Profile


def e(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


TONE = {"good": "#8FCBB6", "fair": "#9CC3D8", "mixed": "#F0BE74", "low": "#E5A08C"}

SCORE_CSS = r"""
.score{position:relative;margin:.5rem 0 0;padding:1.6rem 1.6rem 1.25rem;border:1px solid var(--edge);border-radius:18px;
  background:linear-gradient(160deg,rgba(230,225,214,.06),rgba(230,225,214,.02) 60%);
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);
  box-shadow:0 30px 70px -45px rgba(0,0,0,.9),inset 0 1px 0 rgba(255,255,255,.05);scroll-margin-top:16px}
.score::before{content:"";position:absolute;inset:0;border-radius:inherit;pointer-events:none;
  background:radial-gradient(420px 220px at 8% 0%,var(--lamp-soft),transparent 70%);opacity:.7}
.score>*{position:relative}
.sgrid{display:grid;grid-template-columns:auto minmax(0,1fr);gap:1.5rem 2rem;align-items:center}
.dial{width:148px;text-align:center}
.dial svg{display:block;width:148px;height:148px}
.dial .track{fill:none;stroke:rgba(230,225,214,.10);stroke-width:7}
.dial .arc{fill:none;stroke-width:7;stroke-linecap:round;transform:rotate(-90deg);transform-origin:50% 50%}
.dial .ticks{fill:none;stroke:rgba(230,225,214,.22);stroke-width:1}
.dial .num{font-family:var(--serif);font-weight:300;font-size:40px;fill:var(--stone);letter-spacing:-.02em}
.dial .of{font-size:11px;fill:var(--stone-3);letter-spacing:.12em}
.dial .withheld{fill:none;stroke:rgba(230,225,214,.28);stroke-width:7;stroke-dasharray:2 5}
@media (prefers-reduced-motion:no-preference){.dial .arc{animation:sweep 1.1s cubic-bezier(.5,.1,.2,1) .2s both}}
@keyframes sweep{from{stroke-dasharray:0 100}}
.kicker{margin:0;color:var(--stone-3);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase}
.score h2{font-family:var(--serif);font-weight:400;font-size:clamp(1.5rem,3vw,2rem);margin:.15rem 0 .2rem;letter-spacing:-.01em}
.score h2 .tone{display:inline-block;width:.55em;height:.55em;border-radius:50%;margin-right:.45rem;vertical-align:.12em}
.score .sub2{margin:0;color:var(--stone-2);font-size:.92rem;max-width:40rem}
.comps{list-style:none;margin:1rem 0 0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.9rem}
.comps li{min-width:0}
.comps .cn{display:flex;justify-content:space-between;gap:.5rem;font-size:.84rem;color:var(--stone-2)}
.comps .cn b{font-weight:600;color:var(--stone);font-variant-numeric:tabular-nums}
.comps .w{color:var(--stone-3);font-size:.75rem}
.meter{height:6px;border-radius:99px;background:rgba(230,225,214,.10);margin-top:.4rem;overflow:hidden}
.meter span{display:block;height:100%;border-radius:inherit}
.meter.na{background:repeating-linear-gradient(90deg,rgba(230,225,214,.18) 0 4px,transparent 4px 8px)}
.comps .na-t{color:var(--stone-3);font-size:.8rem;margin-top:.3rem}
.concern{margin:1.1rem 0 0;padding:.6rem .85rem;border-radius:10px;border:1px solid rgba(240,190,116,.35);background:rgba(240,190,116,.07);font-size:.9rem;color:var(--stone)}
.concern a{color:var(--lamp)}
.drivers{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem 2rem;margin-top:1.25rem;padding-top:1.1rem;border-top:1px solid var(--rule)}
.drivers h3{font-family:var(--sans);font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;color:var(--stone-3);font-weight:600;margin:0 0 .5rem}
.drivers ul{list-style:none;margin:0;padding:0;display:grid;gap:.45rem}
.drivers li{position:relative;padding-left:1.4rem;color:var(--stone-2);font-size:.92rem;line-height:1.45}
.drivers li::before{position:absolute;left:0;top:.05em;font-weight:700}
.drivers .up li::before{content:"+";color:#8FCBB6}
.drivers .down li::before{content:"\2212";color:var(--lamp)}
.drivers .need li::before{content:"?";color:var(--stone-3)}
.drivers .pts{color:var(--stone-3);font-size:.8rem;white-space:nowrap}
.inputs{display:flex;flex-wrap:wrap;gap:.75rem 1rem;align-items:flex-end;margin-top:1.25rem;padding-top:1.1rem;border-top:1px solid var(--rule)}
.inputs label{display:grid;gap:.3rem;font-size:.8rem;color:var(--stone-3);letter-spacing:.06em}
.inputs input,.inputs select{background:rgba(10,18,26,.35);border:1px solid var(--edge);border-radius:10px;color:var(--stone);font:inherit;font-size:1rem;padding:.55rem .7rem;min-width:0}
.inputs input{width:11rem}
.inputs input:focus,.inputs select:focus{outline:none;border-color:var(--lamp-line);box-shadow:0 0 0 3px var(--lamp-soft)}
.inputs .btn{padding:.6rem 1rem}
.inputs .prov{flex-basis:100%;margin:0;color:var(--stone-3);font-size:.82rem}
.complete{display:flex;flex-wrap:wrap;align-items:center;gap:.5rem 1rem;margin-top:1rem;font-size:.86rem;color:var(--stone-2)}
.dots{display:inline-flex;gap:4px}
.dots i{width:8px;height:8px;border-radius:2px;background:rgba(230,225,214,.14)}
.dots i.on{background:var(--stone-2)}
.method{margin-top:.9rem}
.method .mbody{margin-top:.6rem;padding:1rem 1.1rem;border-radius:12px;background:rgba(10,18,26,.35);border:1px solid var(--rule);font-size:.9rem;color:var(--stone-2);display:grid;gap:1rem}
.method h4{margin:0 0 .3rem;font-family:var(--serif);font-weight:400;font-size:1.05rem;color:var(--stone)}
.method p{margin:0}
.method ul{margin:.3rem 0 0;padding-left:1.1rem}
.method table{border-collapse:collapse;width:100%;font-size:.85rem;font-variant-numeric:tabular-nums}
.method th,.method td{text-align:left;padding:.3rem .5rem;border-bottom:1px solid var(--rule)}
.method th{color:var(--stone-3);font-weight:600}
.tablewrap{overflow-x:auto}
@media (max-width:760px){
  .score{padding:1.2rem 1rem 1rem}
  .sgrid{grid-template-columns:1fr;justify-items:center;text-align:center}
  .score .sub2{margin:0 auto}
  .comps{grid-template-columns:1fr;text-align:left;width:100%}
  .drivers{grid-template-columns:1fr}
  .inputs input{width:100%}
  .inputs label{flex:1 1 100%}
}
"""


def _dial(s: dict) -> str:
    if s["overall"] is None:
        return ('<div class="dial"><svg viewBox="0 0 132 132" role="img" aria-label="Overall score withheld">'
                '<circle class="withheld" cx="66" cy="66" r="56"/>'
                '<text class="num" x="66" y="74" text-anchor="middle">—</text>'
                '<text class="of" x="66" y="94" text-anchor="middle">WITHHELD</text></svg></div>')
    col = TONE[s["label"]["tone"]]
    ticks = "".join(f'<line x1="66" y1="4" x2="66" y2="9" transform="rotate({a} 66 66)"/>' for a in range(0, 360, 36))
    return ('<div class="dial"><svg viewBox="0 0 132 132" role="img" '
            f'aria-label="Overall ownership score {s["overall"]} out of 100, {e(s["label"]["label"])}">'
            f'<g class="ticks">{ticks}</g><circle class="track" cx="66" cy="66" r="56"/>'
            f'<circle class="arc" cx="66" cy="66" r="56" pathLength="100" stroke="{col}" stroke-dasharray="{s["overall"]} 100"/>'
            f'<text class="num" x="66" y="76" text-anchor="middle">{s["overall"]}</text>'
            '<text class="of" x="66" y="95" text-anchor="middle">OF 100</text></svg></div>')


def _comp_li(c: dict, weight: float) -> str:
    w = f'<span class="w">{int(round(weight * 100))}% of total</span>'
    if not c["available"]:
        return (f'<li><div class="cn"><span>{e(c["name"])}</span><b>—</b></div>'
                f'<div class="meter na" role="img" aria-label="{e(c["name"])}: unavailable"></div>'
                f'<div class="na-t">{e(c.get("status_text") or "Unavailable")}</div>{w}</li>')
    col = TONE[score.label_for(c["score"])["tone"]]
    return (f'<li><div class="cn"><span>{e(c["name"])}</span><b>{c["score"]}</b></div>'
            f'<div class="meter" role="meter" aria-label="{e(c["name"])}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="{c["score"]}">'
            f'<span style="width:{c["score"]}%;background:{col}"></span></div>{w}</li>')


def _pts(d: dict) -> str:
    if d["points"] > 0:
        return f' <span class="pts">−{d["points"]} {e(d["component"] if d["component"] != "major" else "major work")}</span>'
    if d["points"] < 0:
        return f' <span class="pts">+{-d["points"]} {e(d["component"])}</span>'
    return ""


def _drivers(s: dict) -> str:
    helping = s["helping"][:5]
    hurting = s["hurting"][:5]
    col1 = ('<div><h3>Helping</h3><ul class="up">' + "".join(f'<li>{e(d["text"])}{_pts(d)}</li>' for d in helping) + "</ul></div>"
            if helping else '<div><h3>Helping</h3><p class="sub2">Nothing in the available inputs.</p></div>')
    col2 = ('<div><h3>Holding it back</h3><ul class="down">' + "".join(f'<li>{e(d["text"])}{_pts(d)}</li>' for d in hurting) + "</ul></div>"
            if hurting else '<div><h3>Holding it back</h3><p class="sub2">Nothing in the available inputs.</p></div>')
    need = ""
    if s["assumptions"]:
        need += ('<div style="grid-column:1/-1"><h3>Counted cautiously because unknown</h3><ul class="need">' +
                 "".join(f"<li>{e(a)}</li>" for a in s["assumptions"]) + "</ul></div>")
    if s["needed"]:
        need += ('<div style="grid-column:1/-1"><h3>Needed to complete the score</h3><ul class="need">' +
                "".join(f"<li>{e(n)}</li>" for n in s["needed"]) + "</ul></div>")
    return f'<div class="drivers" aria-label="What drives this score">{col1}{col2}{need}</div>'


def _inputs(p: Profile, s: dict) -> str:
    ask = p.get("asking_price")
    hoa = p.get("hoa_exterior")
    val = "" if ask.is_unknown else f"{int(ask.value):,}"
    prov = []
    if not ask.is_unknown:
        prov.append(f"Asking price ${int(ask.value):,} was entered by you on {e((ask.retrieved_date or '')[:10])}; it isn't checked against a listing.")
    if not hoa.is_unknown:
        prov.append("Association answer entered by you.")
    sel = lambda v: " selected" if (hoa.value if not hoa.is_unknown else "unknown") == v else ""
    clear = '<button class="btn ghost" name="action" value="clear">Clear price</button>' if not ask.is_unknown else ""
    return (f'<form class="inputs" method="post" action="/browse/{e(p.house_id)}/inputs" aria-label="Your inputs to the score">'
            f'<label for="ask">ASKING PRICE (YOU PROVIDE)<input id="ask" name="asking_price" inputmode="numeric" placeholder="$ e.g. 345,000" value="{e(val)}"></label>'
            '<label for="hoa">ASSOCIATION HANDLES EXTERIOR UPKEEP?<select id="hoa" name="hoa_exterior">'
            f'<option value="unknown"{sel("unknown")}>Not known</option><option value="no"{sel("no")}>No</option>'
            f'<option value="yes"{sel("yes")}>Yes</option></select></label>'
            f'<button class="btn primary" name="action" value="update">Update score</button>{clear}'
            + (f'<p class="prov">{" ".join(prov)}</p>' if prov else
               '<p class="prov">The price stays on this computer and is labelled as yours; mortgage affordability is not part of this score.</p>')
            + "</form>")


def _provenance(p: Profile) -> str:
    ask, hoa = p.get("asking_price"), p.get("hoa_exterior")
    bits = []
    if not ask.is_unknown:
        bits.append(f"Asking price ${int(ask.value):,} was entered by you on {e((ask.retrieved_date or '')[:10])}; it isn't checked against a listing.")
    if not hoa.is_unknown:
        bits.append("Association answer entered by you: " + e(hoa.value) + ".")
    if not bits:
        bits.append("Enter an asking price above to complete the price part. Mortgage affordability is not part of this score.")
    return '<div class="inputs"><p class="prov">' + " ".join(bits) + "</p></div>"


def _completeness(s: dict) -> str:
    c = s["completeness"]
    dots = "".join('<i class="on"></i>' for _ in range(c["n_known"])) + "".join("<i></i>" for _ in range(c["n"] - c["n_known"]))
    missing = (" Missing: " + ", ".join(c["missing"]) + ".") if c["missing"] else ""
    return (f'<div class="complete"><span class="dots" aria-hidden="true">{dots}</span>'
            f'<span><b>Evidence: {e(c["level"])}</b> — {c["n_known"]} of {c["n"]} key inputs known.{e(missing)} '
            'Completeness is shown separately and does not change the score.</span></div>')


def _method(s: dict) -> str:
    cfg = score.config()
    w = cfg["weights"]
    pc, mc, jc = cfg["price"], cfg["maintenance"], cfg["major"]
    bands = "".join(
        f"<tr><td>{'up to ' + format(b['max_ratio'], '.2f') + '×' if b['max_ratio'] is not None else 'above ' + format(pc['bands'][-2]['max_ratio'], '.2f') + '×'}</td><td>{b['points']}</td></tr>"
        for b in pc["bands"])
    comps = {c["key"]: c for c in s["components"]}
    bench = comps["price"]["inputs"].get("benchmark")
    bench_html = ""
    if bench:
        bf = comps["price"].get("benchmark_field")
        rows = "".join(f"<tr><td>{e(x['date'])}</td><td>${x['price']:,}</td><td>{x['sqft']:,}</td><td>${x['ppsf']}</td></tr>" for x in bench["sales"][:12])
        scope = "assessor neighbourhood " + str(bench["scope_value"]) if bench["scope"] == "neighborhood" else "municipality " + str(bench["scope_value"])
        bench_html = (
            "<div><h4>Price benchmark</h4>"
            f"<p>Median <b>${bench['median_ppsf']}</b> per finished sq ft (middle half ${bench['q1_ppsf']}–${bench['q3_ppsf']}) from "
            f"<b>{bench['n']}</b> valid sales in the {e(scope)}, use “{e(bench['use'])}”, {bench['size_band'][0]:,}–{bench['size_band'][1]:,} sq ft"
            f"{', built within ' + str(pc['era_tolerance_years']) + ' years of this house' if bench.get('era_filter') else ''}, "
            f"sold {e(bench['oldest_sale'])} to {e(bench['newest_sale'])} (window {bench['window_months']} months). "
            f"Retrieved {e((bf.retrieved_date or '')[:10] if bf else '')} from Allegheny County Property Assessments (WPRDC, CC0).</p>"
            f"<p>{e(bf.limitations if bf else '')}</p>"
            f'<div class="tablewrap"><table><thead><tr><th>Sale date</th><th>Price</th><th>Sq ft</th><th>$/sq ft</th></tr></thead><tbody>{rows}</tbody></table></div></div>')
    assumptions = "".join(f"<li>{e(a)}</li>" for a in s["assumptions"]) or "<li>None for this house.</li>"
    assign = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td></tr>" for a, b in score.ASSIGNMENT)
    change = []
    for c in s["components"]:
        for n in c["needed"]:
            change.append(f"{c['name']}: {n}")
    roof = comps["major"].get("roof")
    if roof and roof["state"] == "unknown":
        change.append(f"A documented roof installation date or roofer's report (unknown roof currently counts −{jc['roof']['unknown_points']})")
    if not comps["price"]["inputs"].get("asking_price"):
        change.append("Your asking price")
    change.append("Findings from an inspection report on this house (documented items count −" + str(jc["documented_points"]) + " each)")
    change.append("A different asking price, or new comparable sales in the county record")
    return (
        '<details class="method"><summary>How this score works: method, assumptions and evidence</summary><div class="mbody">'
        f"<div><h4>What it is</h4><p>A 0–100 planning indicator: higher means a more favourable balance of price, ongoing upkeep and "
        f"major-work exposure. It is not an appraisal, an inspection result, a forecast of appreciation, or a recommendation to buy. "
        f"Overall = {int(w['price']*100)}% price position + {int(w['maintenance']*100)}% ongoing maintenance + {int(w['major']*100)}% major-work "
        f"exposure, rounded to the nearest {cfg['overall_display_rounding']} because the inputs can't support more precision. If any part can't be "
        f"assessed, the overall score is withheld instead of reweighting the others. Weights and thresholds are prototype assumptions, "
        f"not validated measures (score config v{cfg['version']}, data/score_config.json).</p></div>"
        "<div><h4>Price position</h4><p>Your asking price per finished sq ft divided by the benchmark median. Points by that ratio "
        "(lower price never scores above the top band — very low prices often reflect condition). Price position and major-work exposure "
        "are separate assessments; together they don't calculate a “true value”.</p>"
        f'<div class="tablewrap"><table><thead><tr><th>Asking ÷ benchmark</th><th>Points</th></tr></thead><tbody>{bands}</tbody></table></div>'
        f"<p>Needs at least {pc['min_comparables']} comparable valid sales within {pc['window_months']} months (or {pc['extended_window_months']} if too few); otherwise “Price assessment unavailable”.</p></div>"
        f"{bench_html}"
        "<div><h4>Ongoing maintenance</h4><p>Starts at 100. Points off: house size "
        + ", ".join(f"{('≤' + format(b['max'], ',')) if b['max'] else 'larger'} sq ft −{b['points']}" for b in mc["size_sqft"])
        + f"; exterior walls brick/stone/masonry −0, frame/stucco/siding −{mc['exterior']['medium']['points']}, log −{mc['exterior']['high']['points']}; "
        f"two or more stories −{mc['stories']['two_or_more_points']}; lot "
        + ", ".join(f"{('≤' + format(b['max'], ',')) if b['max'] else 'larger'} −{b['points']}" for b in mc["lot_sqft"])
        + f"; full or part basement −{mc['basement_points']}; mapped high-risk flood area −{mc['flood_sfha_points']}; mine-subsidence area −{mc['undermined_points']}. "
        f"An association that handles exterior upkeep adds +{mc['shared_exterior_bonus']}. Essential: living area and exterior walls. "
        "Unknown optional inputs take the stated cautious assumption, never zero.</p></div>"
        "<div><h4>Major-work exposure</h4><p>Starts at 100. Points off: each documented major or safety finding on this house "
        f"−{jc['documented_points']} (one per component); roof age established at {jc['roof']['recent_max_age']}–{jc['roof']['past_window_age']-1} years "
        f"−{jc['roof']['planning_points']}, {jc['roof']['past_window_age']}+ years −{jc['roof']['past_window_points']}, under {jc['roof']['recent_max_age']} years or a recent finaled roof permit −0, "
        f"roof age unknown −{jc['roof']['unknown_points']}; assessor condition poor or worse −{jc['assessor_poor_points']}; items needing assessment: "
        f"landslide-prone slope −{jc['assess_points']['slope']}, basement water conditions −{jc['assess_points']['water']}, unfinished permit −{jc['assess_points']['permit']}, "
        f"sale-time sewer test −{jc['assess_points']['sewer']}. A roof's age is never inferred from the construction year. Essential: a matched county parcel record.</p></div>"
        f'<div><h4>Each cost counts once</h4><div class="tablewrap"><table><thead><tr><th>Expense or exposure</th><th>Counted in</th></tr></thead><tbody>{assign}</tbody></table></div></div>'
        f"<div><h4>Assumptions applied to this house</h4><ul>{assumptions}</ul></div>"
        "<div><h4>What would change the score</h4><ul>" + "".join(f"<li>{e(x)}</li>" for x in change) + "</ul></div>"
        "</div></details>")


def panel(p: Profile, *, interactive: bool = True) -> str:
    """interactive=False leaves out the HTML form (the Streamlit app supplies its own widgets)."""
    s = score.compute(p)
    w = s["weights"]
    if s["overall"] is None:
        title = "Score withheld"
        sub = "Not every part can be assessed yet, so there's no overall number. The parts that can be assessed are shown."
        tone = ""
    else:
        title = s["label"]["label"]
        sub = "A planning indicator of price, ongoing upkeep and major-work exposure. Not an appraisal, an inspection, or advice to buy."
        tone = f'<span class="tone" style="background:{TONE[s["label"]["tone"]]}" aria-hidden="true"></span>'
    comps = "".join(_comp_li(c, w[c["key"]]) for c in s["components"])
    concern = ""
    if s["open_major"]:
        doc = f'{s["documented_major"]} documented, ' if s["documented_major"] else ""
        one = s["open_major"] == 1
        concern = (f'<p class="concern">The score doesn&rsquo;t mean the house is free of defects. '
                   f'<a href="#major">{s["open_major"]} potential major {"item" if one else "items"}</a>'
                   f'{" (" + doc.rstrip(", ") + ")" if doc else ""} {"stays" if one else "stay"} listed below, whatever the total.</p>')
    return (f'<section class="score rise d1" id="score" aria-labelledby="h-score">'
            f'<div class="sgrid">{_dial(s)}<div><p class="kicker">HomeKeeper Ownership Score</p>'
            f'<h2 id="h-score">{tone}{e(title)}</h2><p class="sub2">{e(sub)}</p><ul class="comps">{comps}</ul></div></div>'
            f'{concern}{_drivers(s)}{_inputs(p, s) if interactive else _provenance(p)}{_completeness(s)}{_method(s)}</section>')
