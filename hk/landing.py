"""Landing page: the HomeKeeper wordmark, a house drawn in light at dusk, and two choices.

Direction: architectural futurism at dusk. One fine-line elevation of a house on a deep slate
twilight; its windows switch on in sequence once (the single orchestrated motion). The two choices
are dark glass panes that warm like a lit doorway on hover/focus. Fonts: Fraunces (Google Fonts,
free) for the wordmark and choice titles, falling back to the app's serif when offline; system sans
for descriptions. No JavaScript is required; a 20-line enhancement adds a cursor-following light
on pointer devices and is skipped under reduced motion.

Plain string (no f-string) so it parses on Python 3.10+ without escaping concerns.
"""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>HomeKeeper</title>
<meta name="description" content="HomeKeeper — know what your house needs next.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..500,50&display=swap" rel="stylesheet">
<style>
:root{
  --dusk:#1A2633; --dusk-2:#223243; --horizon:#2C3D4F;
  --stone:#E6E1D6; --stone-2:#AEB4B8; --line:rgba(230,225,214,.78); --faint:rgba(230,225,214,.07);
  --lamp:#F0BE74; --lamp-soft:rgba(240,190,116,.16);
  --glass:rgba(230,225,214,.045); --glass-edge:rgba(230,225,214,.16);
  --serif:"Fraunces","Palatino Linotype","Iowan Old Style",Palatino,Georgia,serif;
  --sans:"Segoe UI",system-ui,-apple-system,Helvetica,Arial,sans-serif;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  min-height:100vh;color:var(--stone);font-family:var(--sans);
  background:
    radial-gradient(120% 60% at 50% 108%, rgba(240,190,116,.10), transparent 60%),
    linear-gradient(180deg,var(--dusk) 0%,var(--dusk-2) 58%,var(--horizon) 100%);
  background-color:var(--dusk);
  display:flex;flex-direction:column;overflow-x:hidden;
}
/* a site-plan grid, barely there */
body::before{
  content:"";position:fixed;inset:0;pointer-events:none;
  background-image:
    linear-gradient(var(--faint) 1px,transparent 1px),
    linear-gradient(90deg,var(--faint) 1px,transparent 1px);
  background-size:64px 64px;
  -webkit-mask-image:radial-gradient(80% 70% at 50% 40%,#000 30%,transparent 85%);
          mask-image:radial-gradient(80% 70% at 50% 40%,#000 30%,transparent 85%);
}
main{position:relative;flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
     padding:clamp(1.5rem,5vh,3.5rem) 16px clamp(2rem,6vh,4rem);gap:clamp(1.2rem,3vh,2rem)}

/* ---------- the house ---------- */
.scene{width:min(560px,86vw);position:relative}
.scene svg{display:block;width:100%;height:auto;overflow:visible}
.ln{fill:none;stroke:var(--line);stroke-width:1.15;stroke-linecap:round;stroke-linejoin:round;vector-effect:non-scaling-stroke}
.ln.fine{stroke:rgba(230,225,214,.34);stroke-width:.9}
.ground{stroke:rgba(230,225,214,.42);stroke-width:1;vector-effect:non-scaling-stroke}
.win{fill:var(--lamp);opacity:.9}
.spill{fill:url(#spill)}
@media (prefers-reduced-motion:no-preference){
  .draw{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 1.6s cubic-bezier(.6,.05,.25,1) forwards}
  .draw.d2{animation-delay:.25s}.draw.d3{animation-delay:.5s}.draw.d4{animation-delay:.7s}
  .win{opacity:0;animation:lamp .5s ease-out forwards}
  .w1{animation-delay:1.55s}.w2{animation-delay:1.8s}.w3{animation-delay:2.05s}.w4{animation-delay:2.3s}.w5{animation-delay:2.55s}
  .spill{opacity:0;animation:fade 1.2s ease-out 2s forwards}
  .wordmark{opacity:0;transform:translateY(6px);animation:rise .9s ease-out .9s forwards}
  .choices{opacity:0;animation:fade .8s ease-out 1.4s forwards}
}
@keyframes draw{to{stroke-dashoffset:0}}
@keyframes lamp{0%{opacity:0}60%{opacity:1}100%{opacity:.9}}
@keyframes fade{to{opacity:1}}
@keyframes rise{to{opacity:1;transform:none}}

/* ---------- wordmark ---------- */
.wordmark{margin:0;text-align:center;font-family:var(--serif);font-weight:300;
  font-variation-settings:"opsz" 144,"SOFT" 50;letter-spacing:-.025em;line-height:.95;
  font-size:clamp(3rem,9.5vw,6.6rem);color:var(--stone)}
.wordmark .k{font-weight:400}

/* ---------- choices ---------- */
.choices{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));
  gap:clamp(.8rem,2vw,1.25rem);width:min(760px,100%)}
.choices li{display:flex}.choices li>.choice{flex:1}
.choice{position:relative;display:grid;grid-template-columns:auto 1fr;gap:.35rem 1rem;align-items:start;
  padding:1.35rem 1.4rem 1.4rem;min-height:8.5rem;text-decoration:none;color:inherit;
  background:var(--glass);border:1px solid var(--glass-edge);border-radius:14px;
  -webkit-backdrop-filter:blur(8px) saturate(115%);backdrop-filter:blur(8px) saturate(115%);
  box-shadow:inset 0 1px 0 rgba(255,255,255,.05);overflow:hidden;isolation:isolate;
  transition:border-color .25s ease,transform .25s ease,background-color .25s ease}
/* light spilling from the top edge, like an opened door */
.choice::before{content:"";position:absolute;inset:-1px;z-index:-1;border-radius:inherit;pointer-events:none;
  background:radial-gradient(180px 120px at var(--mx,50%) var(--my,0%),var(--lamp-soft),transparent 70%);
  opacity:0;transition:opacity .3s ease}
.choice:hover,.choice:focus-visible{border-color:rgba(240,190,116,.55);transform:translateY(-2px);background-color:rgba(230,225,214,.06)}
.choice:hover::before,.choice:focus-visible::before{opacity:1}
.choice:focus-visible{outline:2px solid var(--lamp);outline-offset:4px}
.choice:active{transform:translateY(0) scale(.99)}
.icon{grid-row:span 2;width:44px;height:44px;border-radius:10px;display:grid;place-items:center;
  border:1px solid var(--glass-edge);color:var(--stone);transition:color .25s,border-color .25s}
.choice:hover .icon,.choice:focus-visible .icon{color:var(--lamp);border-color:rgba(240,190,116,.45)}
.icon svg{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.4;stroke-linecap:round;stroke-linejoin:round}
.choice .t{font-family:var(--serif);font-weight:400;font-variation-settings:"opsz" 48,"SOFT" 50;
  font-size:1.6rem;line-height:1.1;letter-spacing:-.01em;margin:.1rem 0 0}
.choice .d{font-size:.98rem;line-height:1.45;color:var(--stone-2);margin:0;max-width:30ch}
.choice .go{position:absolute;right:1.1rem;top:1.25rem;width:18px;height:18px;opacity:.45;transition:opacity .25s,transform .25s;
  stroke:currentColor;fill:none;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.choice:hover .go,.choice:focus-visible .go{opacity:1;transform:translate(2px,-2px);color:var(--lamp)}

@media (prefers-reduced-motion:reduce){
  .choice,.choice::before,.icon,.go{transition:none}
  .choice:hover,.choice:focus-visible{transform:none}
}
@media (max-width:640px){
  .scene{width:min(420px,92vw)}
  .choices{grid-template-columns:1fr}
  .choice{min-height:0;padding:1.1rem 1.15rem 1.2rem;grid-template-columns:auto 1fr}
  .choice .t{font-size:1.4rem}
  .wordmark{font-size:clamp(2.7rem,14vw,3.6rem)}
}
@media (max-height:640px) and (min-width:641px){.scene{width:min(420px,60vw)}}
@media (forced-colors:active){.choice{border:1px solid CanvasText}.win{fill:CanvasText}}
</style>
</head>
<body>
<main>
  <div class="scene" aria-hidden="true">
    <svg viewBox="0 0 560 250" role="presentation" focusable="false">
      <defs>
        <radialGradient id="spill" cx="50%" cy="0%" r="60%">
          <stop offset="0" stop-color="#F0BE74" stop-opacity=".28"/>
          <stop offset="1" stop-color="#F0BE74" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <!-- ground and light spill -->
      <ellipse class="spill" cx="280" cy="236" rx="210" ry="22"/>
      <line class="ground draw d4" pathLength="1" x1="20" y1="236" x2="540" y2="236"/>
      <!-- main house: gable front + side wing in two-point-ish elevation -->
      <path class="ln draw" pathLength="1" d="M150 236 V128 L246 62 L342 128 V236"/>
      <path class="ln draw d2" pathLength="1" d="M342 128 L420 102 L452 128 V236 M246 62 L408 40 L452 128"/>
      <path class="ln draw d3" pathLength="1" d="M408 40 L420 102"/>
      <!-- chimney -->
      <path class="ln draw d3" pathLength="1" d="M300 92 V56 H318 V104"/>
      <!-- porch roof and door -->
      <path class="ln draw d2" pathLength="1" d="M206 166 H286 M226 236 V182 H266 V236"/>
      <!-- fine construction lines -->
      <path class="ln fine draw d4" pathLength="1" d="M150 128 H342 M246 62 V128 M60 236 L150 196 M452 196 L520 236"/>
      <!-- windows (lit) -->
      <rect class="win w1" x="234" y="98" width="24" height="22" rx="1.5"/>
      <rect class="win w2" x="170" y="190" width="30" height="30" rx="1.5"/>
      <rect class="win w3" x="292" y="190" width="30" height="30" rx="1.5"/>
      <rect class="win w4" x="364" y="150" width="20" height="26" rx="1.5"/>
      <rect class="win w5" x="404" y="146" width="20" height="26" rx="1.5"/>
      <rect class="win w3" x="236" y="190" width="20" height="40" rx="1.5" opacity=".55"/>
      <!-- window mullions drawn over the light -->
      <path class="ln fine" d="M246 98 V120 M234 109 H258 M185 190 V220 M170 205 H200 M307 190 V220 M292 205 H322"/>
    </svg>
  </div>

  <h1 class="wordmark">Home<span class="k">Keeper</span></h1>

  <ul class="choices" role="list">
    <li>
      <a class="choice" href="/owner">
        <span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3.5 11 12 4l8.5 7"/><path d="M5.5 9.5V20h13V9.5"/><circle cx="12" cy="13.5" r="1.6"/><path d="M12 15.1V18"/></svg></span>
        <span class="t">Homeowner</span>
        <span class="d">See what your house needs next, and why.</span>
        <svg class="go" viewBox="0 0 18 18" aria-hidden="true"><path d="M5 13 13 5M7 5h6v6"/></svg>
      </a>
    </li>
    <li>
      <a class="choice" href="/browse">
        <span class="icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M3 11.5 10 5.5l7 6"/><path d="M5 10v8.5h6"/><circle cx="16.5" cy="16" r="3"/><path d="m18.7 18.2 2.3 2.3"/></svg></span>
        <span class="t">Browse Homes</span>
        <span class="d">Check a home you&rsquo;re considering before you buy.</span>
        <svg class="go" viewBox="0 0 18 18" aria-hidden="true"><path d="M5 13 13 5M7 5h6v6"/></svg>
      </a>
    </li>
  </ul>
</main>
<script>
/* Cursor-following light on the two choices; pointer devices only, skipped under reduced motion. */
(function(){
  if (!window.matchMedia || matchMedia('(prefers-reduced-motion: reduce)').matches || !matchMedia('(hover: hover)').matches) return;
  document.querySelectorAll('.choice').forEach(function(el){
    el.addEventListener('pointermove', function(ev){
      var r = el.getBoundingClientRect();
      el.style.setProperty('--mx', ((ev.clientX - r.left) / r.width * 100).toFixed(1) + '%');
      el.style.setProperty('--my', ((ev.clientY - r.top) / r.height * 100).toFixed(1) + '%');
    });
    el.addEventListener('pointerleave', function(){ el.style.removeProperty('--mx'); el.style.removeProperty('--my'); });
  });
})();
</script>
</body>
</html>
"""


def landing_page() -> str:
    return PAGE


def hero_css() -> str:
    """The house drawing and wordmark styles (for reuse in the Streamlit app)."""
    css = PAGE.split("<style>", 1)[1].split("</style>", 1)[0]
    root = css[:css.index("*{box-sizing")]  # :root tokens
    house = css[css.index("/* ---------- the house"):css.index("/* ---------- choices")]
    return root + house + ".hero{display:flex;flex-direction:column;align-items:center;gap:1rem;padding:.5rem 0 1rem}"


def hero_html() -> str:
    """The lit house elevation and the HomeKeeper wordmark, as on the landing page."""
    main = PAGE.split("<main>", 1)[1]
    scene = main[main.index('<div class="scene"'):main.index('<h1 class="wordmark"')]
    word = main[main.index('<h1 class="wordmark"'):]
    word = word[:word.index("</h1>") + 5]
    return '<div class="hero">' + scene + word + "</div>"


def choice_css() -> str:
    """Styles for the two choice cards, without the link hover (the Streamlit app puts a button under each)."""
    css = PAGE.split("<style>", 1)[1].split("</style>", 1)[0]
    block = css[css.index("/* ---------- choices"):css.index("@media (prefers-reduced-motion:reduce)")]
    return block + ".choice.static{min-height:0;cursor:default}.choice.static:hover{transform:none;border-color:var(--glass-edge);background-color:var(--glass)}"


def choice_card(which: str) -> str:
    """'owner' or 'browse': the landing page's card markup as a static block."""
    main = PAGE.split('<ul class="choices"', 1)[1]
    href = {"owner": 'href="/owner"', "browse": 'href="/browse"'}[which]
    a = main[main.index('<a class="choice" ' + href):]
    a = a[:a.index("</a>")]
    a = a.replace('<a class="choice" ' + href + '>', '<div class="choice static">')
    a = a[:a.index('<svg class="go"')]
    return a + "</div>"
