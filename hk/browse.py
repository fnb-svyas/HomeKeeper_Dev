"""Browse Homes: a prospective buyer's overview, in the landing page's dusk theme.

The page answers "what would owning this house involve?" from the buyer overview in hk/buyer.py.
It has no task controls (no Done, snooze, reminders or calendars) and no routine maintenance items.
Supporting evidence opens in place with <details>, so nobody loses their place.
"""
from __future__ import annotations

import html
from typing import Optional

from . import buyer, score_view
from .evidence import Profile


def e(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


CSS = r"""
:root{
  --dusk:#1A2633; --dusk-2:#223243; --horizon:#2C3D4F;
  --stone:#E6E1D6; --stone-2:#AEB4B8; --stone-3:#8C969E; --faint:rgba(230,225,214,.06);
  --lamp:#F0BE74; --lamp-soft:rgba(240,190,116,.14); --lamp-line:rgba(240,190,116,.55);
  --sky:#9CC3D8; --sky-soft:rgba(156,195,216,.12);
  --glass:rgba(230,225,214,.04); --glass-2:rgba(230,225,214,.07); --edge:rgba(230,225,214,.14); --rule:rgba(230,225,214,.12);
  --serif:"Fraunces","Palatino Linotype","Iowan Old Style",Palatino,Georgia,serif;
  --sans:"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;
  color-scheme:dark;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body{margin:0;min-height:100vh;color:var(--stone);font:16px/1.6 var(--sans);overflow-x:hidden;
  background:radial-gradient(90% 50% at 50% -10%, rgba(156,195,216,.08), transparent 70%),
             linear-gradient(180deg,var(--dusk) 0,var(--dusk-2) 900px,var(--dusk) 100%);
  background-color:var(--dusk)}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(var(--faint) 1px,transparent 1px),linear-gradient(90deg,var(--faint) 1px,transparent 1px);
  background-size:64px 64px;
  -webkit-mask-image:linear-gradient(180deg,#000 0,rgba(0,0,0,.35) 40%,transparent 80%);
          mask-image:linear-gradient(180deg,#000 0,rgba(0,0,0,.35) 40%,transparent 80%)}
a{color:var(--stone);text-decoration-color:rgba(230,225,214,.35);text-underline-offset:3px}
a:hover{text-decoration-color:var(--lamp)}
:focus-visible{outline:2px solid var(--lamp);outline-offset:3px;border-radius:6px}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.skip{position:absolute;left:16px;top:-48px;background:var(--lamp);color:#1A2633;padding:.4rem .8rem;border-radius:8px;z-index:5}
.skip:focus{top:12px}
.wrap{position:relative;z-index:1;width:min(1040px,100%);margin:0 auto;padding:0 24px}

/* top bar */
.bar{display:flex;align-items:center;gap:1rem;padding:18px 0}
.mark{font-family:var(--serif);font-size:1.35rem;font-weight:400;letter-spacing:-.01em;text-decoration:none;color:var(--stone)}
.mark span{font-weight:500}
.ctx{color:var(--stone-3);font-size:.85rem;letter-spacing:.14em;text-transform:uppercase;padding-left:1rem;border-left:1px solid var(--rule)}
.bar .alt{margin-left:auto;font-size:.9rem;color:var(--stone-2)}

/* search */
.find{padding:clamp(1.5rem,5vh,3rem) 0 1.25rem}
.find h1{font-family:var(--serif);font-weight:300;font-size:clamp(2.2rem,5.2vw,3.6rem);line-height:1.05;letter-spacing:-.02em;margin:0 0 .6rem;
  font-variation-settings:"opsz" 144,"SOFT" 50}
.find .intro{color:var(--stone-2);max-width:40rem;margin:0 0 1.5rem;font-size:1.05rem}
.search{display:flex;gap:.6rem;align-items:stretch;padding:.45rem;border-radius:16px;background:var(--glass-2);border:1px solid var(--edge);
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);box-shadow:0 18px 50px -30px rgba(0,0,0,.8),inset 0 1px 0 rgba(255,255,255,.04);
  transition:border-color .2s ease,box-shadow .2s ease}
.search:focus-within{border-color:var(--lamp-line);box-shadow:0 0 0 4px var(--lamp-soft),0 18px 50px -30px rgba(0,0,0,.8)}
.search .ico{flex:none;align-self:center;margin-left:.6rem;color:var(--stone-3)}
.search input{flex:1;min-width:0;background:transparent;border:0;color:var(--stone);font:inherit;font-size:1.05rem;padding:.7rem .4rem}
.search input::placeholder{color:var(--stone-3)}
.search input:focus{outline:none}
.btn{appearance:none;border:1px solid transparent;border-radius:11px;font:inherit;font-weight:600;cursor:pointer;padding:.7rem 1.25rem;
  transition:background-color .2s ease,border-color .2s ease,transform .15s ease}
.btn.primary{background:var(--lamp);color:#1E2A36}
.btn.primary:hover{background:#F5CD8F}
.btn.primary:disabled{opacity:.7;cursor:progress}
.btn.ghost{background:transparent;color:var(--stone);border-color:var(--edge)}
.btn.ghost:hover{border-color:var(--lamp-line);background:var(--lamp-soft)}
.btn:active{transform:scale(.98)}
.hint{color:var(--stone-3);font-size:.88rem;margin:.6rem .2rem 0}
.recent{display:flex;flex-wrap:wrap;align-items:center;gap:.45rem;margin-top:1rem}
.recent .lbl{color:var(--stone-3);font-size:.78rem;letter-spacing:.12em;text-transform:uppercase;margin-right:.3rem}
.chip{display:inline-flex;align-items:center;gap:.4rem;padding:.32rem .75rem;border-radius:999px;border:1px solid var(--edge);
  background:var(--glass);font-size:.88rem;text-decoration:none;color:var(--stone-2);transition:border-color .2s,color .2s,background-color .2s}
.chip:hover{border-color:var(--lamp-line);color:var(--stone)}
.chip[aria-current="page"]{border-color:var(--lamp-line);color:var(--stone);background:var(--lamp-soft)}
.examples{margin-top:1.25rem;color:var(--stone-3);font-size:.9rem;display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
.examples form{display:inline}
.linkbtn{appearance:none;background:none;border:0;padding:0;font:inherit;color:var(--stone-2);text-decoration:underline;
  text-decoration-color:rgba(230,225,214,.3);text-underline-offset:3px;cursor:pointer}
.linkbtn:hover{color:var(--stone);text-decoration-color:var(--lamp)}
.notice{border:1px solid var(--edge);border-left:3px solid var(--lamp);background:var(--glass);padding:.7rem 1rem;border-radius:10px;margin:0 0 1rem;color:var(--stone)}

/* property */
.prop{padding:1.5rem 0 3rem}
.head{position:relative;padding:2rem 0 1.75rem;border-top:1px solid var(--rule)}
.head::before{content:"";position:absolute;left:0;top:-1px;width:72px;height:1px;background:var(--lamp)}
.eyebrow{margin:0 0 .5rem;color:var(--stone-3);font-size:.8rem;letter-spacing:.14em;text-transform:uppercase}
.tag{display:inline-block;margin-left:.5rem;padding:.05rem .5rem;border-radius:6px;border:1px solid var(--lamp-line);color:var(--lamp);letter-spacing:.08em}
.head h1{font-family:var(--serif);font-weight:300;font-size:clamp(2rem,5vw,3.25rem);line-height:1.05;letter-spacing:-.02em;margin:0;
  font-variation-settings:"opsz" 144,"SOFT" 50}
.head .addr2{margin:.25rem 0 0;color:var(--stone-2);font-size:1.05rem}
.lede{font-family:var(--serif);font-size:clamp(1.15rem,2.2vw,1.4rem);line-height:1.45;max-width:46rem;margin:1.25rem 0 0;font-weight:350;color:var(--stone)}
.jump{display:flex;flex-wrap:wrap;gap:.4rem 1.25rem;margin:1.25rem 0 0;padding:0;list-style:none;font-size:.9rem}
.jump a{color:var(--stone-2);text-decoration:none;display:inline-flex;gap:.45rem;align-items:baseline}
.jump a:hover{color:var(--stone)}
.jump .n{font-variant-numeric:tabular-nums;color:var(--lamp);font-size:.78rem;letter-spacing:.08em}
.fine{color:var(--stone-3);font-size:.85rem;margin:1rem 0 0;max-width:46rem}

section.part{position:relative;padding:2.5rem 0 .5rem;scroll-margin-top:16px}
.part>h2{display:flex;align-items:baseline;gap:.9rem;margin:0 0 .35rem;font-family:var(--serif);font-weight:400;font-size:clamp(1.45rem,3vw,1.85rem);letter-spacing:-.01em}
.part>h2 .n{font-family:var(--sans);font-size:.78rem;letter-spacing:.14em;color:var(--lamp);font-variant-numeric:tabular-nums}
.part>h2::after{content:"";flex:1;height:1px;align-self:center;background:linear-gradient(90deg,var(--rule),transparent)}
.part>.sub{color:var(--stone-2);margin:0 0 1.25rem;max-width:44rem}

/* A: facts */
.facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;margin:0;border:1px solid var(--rule);border-radius:14px;overflow:hidden;background:var(--rule)}
.fact{background:linear-gradient(180deg,rgba(34,50,67,.96),rgba(30,45,60,.96));padding:.9rem 1rem 1rem;min-width:0}
.fact dt{font-size:.75rem;letter-spacing:.1em;text-transform:uppercase;color:var(--stone-3);margin:0 0 .25rem}
.fact dd{margin:0;font-size:1.02rem;overflow-wrap:anywhere}
.fact dd small{display:block;color:var(--stone-3);font-size:.78rem;line-height:1.4;margin-top:.25rem}
.fact.unk dd{color:var(--stone-3);font-style:italic}
.site{list-style:none;padding:0;margin:1rem 0 0;display:flex;flex-wrap:wrap;gap:.5rem}
.site li{display:inline-flex;align-items:center;gap:.5rem;padding:.4rem .8rem;border-radius:999px;border:1px solid var(--edge);background:var(--glass);font-size:.9rem;color:var(--stone-2)}
.site li::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--stone-3)}
.site li.flag{color:var(--stone);border-color:rgba(240,190,116,.35)}
.site li.flag::before{background:var(--lamp)}
.site li.clear::before{background:var(--sky)}

/* B: major work */
.legend{display:flex;flex-wrap:wrap;gap:.4rem 1.25rem;margin:0 0 1rem;padding:0;list-style:none;color:var(--stone-3);font-size:.85rem}
.legend b{font-weight:600}
.works{display:grid;gap:.9rem}
.work{position:relative;padding:1.2rem 1.35rem 1.1rem;border:1px solid var(--edge);border-radius:14px;background:var(--glass);
  -webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);box-shadow:inset 0 1px 0 rgba(255,255,255,.04);transition:border-color .25s ease}
.work:hover{border-color:rgba(230,225,214,.24)}
.work.s-documented{border-left:3px solid var(--lamp)}
.work.s-planning{border-left:3px solid var(--sky)}
.work.s-assess{border-left:3px solid rgba(230,225,214,.5)}
.work .top{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center;margin-bottom:.45rem}
.pill{font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;padding:.18rem .55rem;border-radius:6px;border:1px solid var(--edge);color:var(--stone-2)}
.pill.documented{color:var(--lamp);border-color:var(--lamp-line)}
.pill.planning{color:var(--sky);border-color:rgba(156,195,216,.5)}
.when{font-size:.85rem;color:var(--stone-2)}
.when::before{content:"◷ ";color:var(--stone-3)}
.work h3,.theme h3,.qs h3{font-family:var(--serif);font-weight:400;font-size:1.25rem;line-height:1.3;margin:0 0 .35rem}
.work p,.theme p,.qs p{margin:0;color:var(--stone-2)}
.work .cost{margin-top:.55rem;font-size:.9rem;color:var(--stone-3)}
.empty{padding:1.25rem 1.35rem;border:1px dashed var(--edge);border-radius:14px;color:var(--stone-2)}
.empty b{color:var(--stone);font-weight:600}
.caveat{color:var(--stone-3);font-size:.9rem;margin:1rem 0 0;max-width:46rem}

/* C: ownership */
.themes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.5rem 2.25rem}
.theme{padding-top:.9rem;border-top:1px solid var(--rule)}
.theme h3{font-size:1.1rem}

/* D: unknowns */
.qs{list-style:none;margin:0;padding:0;counter-reset:q;display:grid;gap:.25rem}
.qs>li{position:relative;padding:1rem 0 1rem 3.1rem;border-top:1px solid var(--rule);counter-increment:q}
.qs>li::before{content:counter(q,decimal-leading-zero);position:absolute;left:0;top:1.15rem;font-size:.8rem;letter-spacing:.1em;color:var(--lamp);font-variant-numeric:tabular-nums}
.qs h3{font-size:1.15rem}
details.more>summary{margin-top:.75rem}

/* evidence, opened in place */
details.ev{margin-top:.6rem}
details>summary{cursor:pointer;list-style:none;display:inline-flex;align-items:center;gap:.4rem;font-size:.85rem;color:var(--stone-2);
  padding:.2rem .1rem;border-radius:6px}
details>summary::-webkit-details-marker{display:none}
details>summary::before{content:"";width:6px;height:6px;border-right:1.5px solid currentColor;border-bottom:1.5px solid currentColor;transform:rotate(-45deg);transition:transform .2s ease;margin-right:.15rem}
details[open]>summary::before{transform:rotate(45deg)}
details>summary:hover{color:var(--stone)}
.evl{list-style:none;margin:.5rem 0 0;padding:.75rem .9rem;border-radius:10px;background:rgba(10,18,26,.35);border:1px solid var(--rule);display:grid;gap:.6rem;font-size:.86rem}
.evl li{display:grid;gap:.1rem}
.evl b{font-weight:600;color:var(--stone)}
.evl .src{color:var(--stone-2)}
.evl .lim{color:var(--stone-3)}

/* secondary */
.after{margin-top:3rem;padding:1.5rem;border:1px solid var(--rule);border-radius:14px;display:flex;flex-wrap:wrap;gap:1rem 1.5rem;align-items:center;justify-content:space-between;background:var(--glass)}
.after p{margin:0;color:var(--stone-2);max-width:34rem}
.after form{margin:0}
.choose{display:grid;gap:.5rem;margin-top:1rem}
.choose button{text-align:left}
footer.foot{position:relative;z-index:1;color:var(--stone-3);font-size:.8rem;padding:2rem 0 2.5rem;border-top:1px solid var(--rule);margin-top:2rem}

@media (prefers-reduced-motion:no-preference){
  .rise{opacity:0;transform:translateY(8px);animation:rise .6s ease-out forwards}
  .rise.d1{animation-delay:.06s}.rise.d2{animation-delay:.12s}.rise.d3{animation-delay:.18s}.rise.d4{animation-delay:.24s}
}
@keyframes rise{to{opacity:1;transform:none}}

@media (max-width:860px){.facts{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){
  .wrap{padding:0 16px}
  .ctx{display:none}
  .search{flex-wrap:wrap}
  .search .ico{display:none}
  .search input{flex-basis:100%;padding:.65rem .6rem}
  .search .btn{flex:1}
  .themes{grid-template-columns:1fr}
  .qs>li{padding-left:2.4rem}
  .work{padding:1.05rem 1.05rem 1rem}
}
@media (forced-colors:active){.search,.work,.chip,.pill{border:1px solid CanvasText}}
"""

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..500,50&display=swap" rel="stylesheet">')

SEARCH_ICON = ('<svg class="ico" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" '
               'stroke-linecap="round" aria-hidden="true"><path d="M3 11 12 4l9 7"/><path d="M5 10v9h6"/><circle cx="16.5" cy="16.5" r="3.2"/><path d="m19 19 2.2 2.2"/></svg>')

SUBMIT_JS = "var b=this.querySelector('button');b.disabled=true;b.textContent='Looking up the record…';"


def _page(title: str, body: str) -> str:
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>{e(title)}</title>{FONTS}<style>{CSS}{score_view.SCORE_CSS}</style></head><body>"
            '<a class="skip" href="#main">Skip to content</a>'
            '<div class="wrap"><header class="bar"><a class="mark" href="/" aria-label="HomeKeeper home">Home<span>Keeper</span></a>'
            '<span class="ctx">Browse homes</span><a class="alt" href="/owner">I own a home</a></header>'
            f'<main id="main">{body}</main>'
            '<footer class="foot">Built from public records and mapped data for Allegheny County. Not an inspection or an appraisal; '
            'verify anything that matters with the seller, your inspector and the municipality.</footer></div></body></html>')


def _search(recents: list[tuple[str, str]], current: Optional[str], *, big: bool) -> str:
    chips = ""
    if recents:
        links = "".join(
            f'<a class="chip" href="/browse/{e(hid)}"{" aria-current=" + chr(34) + "page" + chr(34) if hid == current else ""}>{e(label)}</a>'
            for hid, label in recents)
        chips = f'<nav class="recent" aria-label="Homes you have looked up"><span class="lbl">Looked up</span>{links}</nav>'
    head = ""
    if big:
        head = ('<h1 class="rise">What would owning it involve?</h1>'
                '<p class="intro rise d1">Enter the address of a home you&rsquo;re considering. You&rsquo;ll see the property at a glance, '
                'any major work the record points to, what upkeep it asks of an owner, and what to settle before you buy.</p>')
    return (f'<section class="find" aria-label="Look up a home">{head}'
            f'<form method="post" action="/build" class="search{" rise d2" if big else ""}" role="search" onsubmit="{e(SUBMIT_JS)}">'
            '<input type="hidden" name="mode" value="browse">'
            f'{SEARCH_ICON}<label class="sr" for="addr">Address of the home</label>'
            '<input id="addr" name="address" placeholder="Address, e.g. 123 Main St, Pittsburgh, PA 15228" autocomplete="street-address" required'
            f'{" autofocus" if big else ""}>'
            '<button class="btn primary">Look up</button></form>'
            '<p class="hint">Allegheny County addresses. HomeKeeper doesn&rsquo;t list homes for sale &mdash; bring the address from your listing site or agent.</p>'
            f'{chips}</section>')


def _evidence(evs: list[dict], label: str = "Evidence") -> str:
    evs = [x for x in evs if x]
    if not evs:
        return ""
    items = []
    for x in evs:
        src = " · ".join(s for s in (x.get("source"), ("retrieved " + str(x["retrieved"])[:10]) if x.get("retrieved") else "") if s)
        items.append(f'<li><b>{e(x.get("said"))}</b>' + (f'<span class="src">{e(src)}</span>' if src else "") +
                     (f'<span class="lim">{e(x.get("limits"))}</span>' if x.get("limits") else "") + "</li>")
    return f'<details class="ev"><summary>{e(label)} ({len(evs)})</summary><ul class="evl">{"".join(items)}</ul></details>'


def _glance(o: dict) -> str:
    g = o["glance"]
    facts = []
    for r in g["rows"]:
        small = f'<small>{e(r["extra"])}</small>' if r.get("extra") and r["known"] else ""
        facts.append(f'<div class="fact{"" if r["known"] else " unk"}"><dt>{e(r["label"])}</dt><dd>{e(r["value"])}{small}</dd></div>')
    site = "".join(
        f'<li class="{"flag" if s["flag"] else "clear" if s["flag"] is False else ""}">{e(s["text"])}</li>' for s in g["site"])
    evs = [r["ev"] for r in g["rows"] if r.get("ev")] + [s["ev"] for s in g["site"] if s.get("ev")]
    return ('<section class="part" id="glance" aria-labelledby="h-glance">'
            '<h2 id="h-glance"><span class="n">01</span>Property at a glance</h2>'
            '<p class="sub">What the public record says. Anything it doesn&rsquo;t say stays marked &ldquo;Not recorded&rdquo;.</p>'
            f'<dl class="facts">{"".join(facts)}</dl>'
            f'<ul class="site" aria-label="Site and location">{site}</ul>'
            f'{_evidence(evs, "Where these facts come from")}</section>')


def _cost(it: dict) -> str:
    est = it.get("cost")
    if est:
        return (f'<p class="cost">Cost: ${est["low"]:,.0f}–${est["high"]:,.0f} ({e(est["basis"].replace("_", " "))}; '
                f'scope: {e(est["scope"])}; {e(est.get("source") or "")}, {e(est.get("date") or "")})</p>')
    if it.get("cost_note"):
        return f'<p class="cost">{e(it["cost_note"])}</p>'
    return '<p class="cost">No cost range: there is no scoped quote for this house and no licensed local cost source.</p>'


def _major(o: dict) -> str:
    legend = ('<ul class="legend" aria-label="What the labels mean">'
              '<li><b>Documented need</b> — in a report or record for this house</li>'
              '<li><b>Planning consideration</b> — established facts make it worth budgeting for</li>'
              '<li><b>Needs assessment</b> — the evidence points here; a professional has to look</li></ul>')
    if o["major"]:
        cards = []
        for it in o["major"]:
            when = f'<span class="when">{e(it["timing"])}</span>' if it.get("timing") else ""
            cards.append(f'<article class="work s-{e(it["status"])}"><div class="top"><span class="pill {e(it["status"])}">'
                         f'{e(buyer.STATUS[it["status"]])}</span>{when}</div><h3>{e(it["title"])}</h3><p>{e(it["what"])}</p>'
                         f'{_cost(it)}{_evidence(it["evidence"])}</article>')
        body = legend + f'<div class="works">{"".join(cards)}</div>'
    else:
        body = ('<div class="empty"><b>The record doesn&rsquo;t establish any major project for this house.</b> '
                'That isn&rsquo;t a clean bill of health: an absence of records is not an absence of problems.</div>')
    return ('<section class="part" id="major" aria-labelledby="h-major">'
            '<h2 id="h-major"><span class="n">02</span>Potential major work</h2>'
            '<p class="sub">Substantial projects, listed only where a specific piece of evidence points to them.</p>'
            f'{body}<p class="caveat">The public record doesn&rsquo;t describe the condition of the roof, foundation, windows, siding or '
            'driveway, so none of those appear here unless something specific does. Optional upgrades aren&rsquo;t listed.</p></section>')


def _ownership(o: dict) -> str:
    items = "".join(f'<div class="theme"><h3>{e(t["title"])}</h3><p>{e(t["text"])}</p>{_evidence(t["evidence"], "Basis")}</div>'
                    for t in o["ownership"])
    return ('<section class="part" id="ownership" aria-labelledby="h-own">'
            '<h2 id="h-own"><span class="n">03</span>Owning and keeping it up</h2>'
            '<p class="sub">The general upkeep this house would ask of you, in plain terms. Not a task list.</p>'
            f'<div class="themes">{items}</div></section>')


def _q(u: dict) -> str:
    return f'<li><h3>{e(u["q"])}</h3><p>{e(u["why"])}</p>{_evidence(u.get("evidence") or [], "Basis")}</li>'


def _unknowns(o: dict) -> str:
    qs = o["unknowns"]
    top, rest = qs[:5], qs[5:]
    more = ""
    if rest:
        more = (f'<details class="more"><summary>{len(rest)} more {"question" if len(rest) == 1 else "questions"}</summary>'
                f'<ol class="qs" start="6">{"".join(_q(u) for u in rest)}</ol></details>')
    return ('<section class="part" id="unknowns" aria-labelledby="h-unk">'
            '<h2 id="h-unk"><span class="n">04</span>Settle before you buy</h2>'
            '<p class="sub">Open questions that could change the picture. Ask the seller, your agent and your inspector.</p>'
            f'<ol class="qs">{"".join(_q(u) for u in top)}</ol>{more}</section>')


def _match_panel(p: Profile) -> str:
    m = p.match or {}
    cands = m.get("candidates") or []
    if m.get("ambiguous") and cands:
        btns = "".join(
            f'<button class="btn ghost" name="choose" value="{i}">{e(c.get("address") if isinstance(c, dict) else c)}</button>'
            for i, c in enumerate(cands))
        return ('<div class="notice" role="status"><b>This address matched more than one property.</b> Choose the one you mean:'
                f'<form method="post" action="/browse/{e(p.house_id)}/choose" class="choose">{btns}</form></div>')
    if not cands or m.get("chosen") is None and not m.get("ambiguous") and p.get("parcel_id").is_unknown:
        return ('<div class="notice" role="status">This address couldn&rsquo;t be matched to a county parcel, so most facts below are '
                'unknown. Check the spelling and include the ZIP code.</div>')
    return ""


def _jump() -> str:
    links = [("score", "—", "Score"), ("glance", "01", "At a glance"), ("major", "02", "Major work"), ("ownership", "03", "Upkeep"),
             ("unknowns", "04", "Before you buy")]
    return '<ul class="jump" aria-label="On this page">' + "".join(
        f'<li><a href="#{a}"><span class="n">{n}</span>{t}</a></li>' for a, n, t in links) + "</ul>"


def browse_index(recents: list[tuple[str, str]], msg: str = "") -> str:
    notice = f'<p class="notice" role="status">{e(msg)}</p>' if msg else ""
    ex = ('<div class="examples rise d3"><span>No address handy? Open an invented example:</span>'
          '<form method="post" action="/sample"><input type="hidden" name="mode" value="browse"><input type="hidden" name="name" value="complete">'
          '<button class="linkbtn">a 1928 brick colonial</button></form><span aria-hidden="true">·</span>'
          '<form method="post" action="/sample"><input type="hidden" name="mode" value="browse"><input type="hidden" name="name" value="missing">'
          '<button class="linkbtn">a house with a sparse record</button></form></div>')
    return _page("Browse homes — HomeKeeper", notice + _search(recents, None, big=True) + ex)


def browse_property(p: Profile, recents: list[tuple[str, str]], msg: str = "") -> str:
    notice = f'<p class="notice" role="status">{e(msg)}</p>' if msg else ""
    addr = buyer.address(p)
    body = notice + _search(recents, p.house_id, big=False) + property_article(p)
    return _page(addr.split(",")[0] + " — Browse homes — HomeKeeper", body)


def property_article(p: Profile, *, interactive: bool = True) -> str:
    """The property overview (header, score, sections A-D). interactive=False leaves out HTML forms."""
    o = buyer.overview(p)
    addr = o["address"]
    first, _, rest = addr.partition(",")
    g = {r["field"]: r for r in o["glance"]["rows"]}
    eyebrow_bits = [g[k]["value"] for k in ("use_description", "municipality") if g[k]["known"]]
    demo = '<span class="tag">Invented example</span>' if o["synthetic"] else ""
    head = (f'<header class="head rise">'
            f'<p class="eyebrow">{e(" · ".join(eyebrow_bits) or "Property")}{demo}</p>'
            f'<h1>{e(first)}</h1>' + (f'<p class="addr2">{e(rest.strip(" ,"))}</p>' if rest.strip() else "") +
            f'<p class="lede">{e(o["summary"])}</p>{_jump()}'
            f'<p class="fine">From the public record and mapped data, retrieved {e(str(o["retrieved"])[:10])}. Not an inspection. '
            'Nothing here comes from a homeowner&rsquo;s private records.</p></header>')
    after = ('<aside class="after" aria-label="If you buy it"><p>Bought this home, or under contract? HomeKeeper can keep its maintenance '
             'plan and records for you.</p>'
             f'<form method="post" action="/build"><input type="hidden" name="address" value="{e(p.address_input)}">'
             '<button class="btn ghost">Track it as my home</button></form></aside>')
    if not interactive:
        after = ""
    return (f'<article class="prop" aria-label="{e(addr)}">{head}{_match_panel(p) if interactive else ""}'
            f'{score_view.panel(p, interactive=interactive)}'
            f'{_glance(o)}{_major(o)}{_ownership(o)}{_unknowns(o)}{after}</article>')


def standalone_css() -> str:
    """Stylesheet for embedding the overview in another host (the Streamlit app)."""
    return CSS + score_view.SCORE_CSS


def recents(ids: list[str]) -> list[tuple[str, str]]:
    out = []
    for i in ids:
        try:
            p = Profile.load(i)
        except Exception:
            continue
        if p.value("stage") == "before_buy":
            out.append((i, buyer.address(p).split(",")[0] + (" (example)" if p.synthetic else "")))
    return out
