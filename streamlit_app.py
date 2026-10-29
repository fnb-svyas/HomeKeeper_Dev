"""HomeKeeper — Browse Homes with the Ownership Score, as a Streamlit app.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud -> New app -> this repository -> main file: streamlit_app.py

Opens on the HomeKeeper home page with two choices: Homeowner (a read-only preview of the plan) and
Browse Homes (the buyer's overview and Ownership Score), both from public-record data.
Each visitor's lookups and asking prices are kept under their own session id on the server's
disk; they are temporary and disappear when the app restarts. The homeowner side stays in the
local app (python server.py).
"""
from __future__ import annotations

import pathlib
import re
import sys
import threading
import uuid

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from hk import browse, buyer, builder, http as hk_http, landing, records, samples, score, web3  # noqa: E402
from hk.evidence import Profile, slug  # noqa: E402

st.set_page_config(page_title="HomeKeeper — Browse homes", page_icon="🏠", layout="wide")

EXAMPLES = {"complete": "Example: 1928 brick colonial", "missing": "Example: sparse city record"}
HOA_CHOICES = {"Not known": "unknown", "No": "no", "Yes": "yes"}

# Streamlit's own layout, restyled to the HomeKeeper dusk theme. These rules don't depend on
# .streamlit/config.toml, so the look holds even if that file is missing from the repository.
APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght,SOFT@9..144,300..500,50&display=swap');
body::before{display:none}
[data-testid="stApp"]{color:#E6E1D6;
  background:radial-gradient(120% 50% at 50% 0%, rgba(156,195,216,.07), transparent 70%),
             linear-gradient(180deg,#1A2633 0,#223243 900px,#1E2D3C 100%) !important}
[data-testid="stApp"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:linear-gradient(rgba(230,225,214,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(230,225,214,.05) 1px,transparent 1px);
  background-size:64px 64px;-webkit-mask-image:linear-gradient(180deg,#000,transparent 75%);mask-image:linear-gradient(180deg,#000,transparent 75%)}
[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stBottom"]>div{background:transparent !important}
[data-testid="stHeader"]{background:transparent !important}
[data-testid="stDecoration"]{display:none}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1080px;padding-top:4.5rem !important;position:relative;z-index:1}
[data-testid="stForm"]{border:1px solid rgba(230,225,214,.14) !important;border-radius:16px !important;background:rgba(230,225,214,.05) !important;padding:1rem 1.1rem !important}
[data-testid="stWidgetLabel"] p{color:#AEB4B8 !important;font-size:.82rem !important;letter-spacing:.04em}
[data-baseweb="input"],[data-baseweb="base-input"],[data-baseweb="select"]>div{background:rgba(10,18,26,.4) !important;border-color:rgba(230,225,214,.16) !important;border-radius:10px !important}
[data-baseweb="input"] input,[data-baseweb="select"] *{color:#E6E1D6 !important}
[data-baseweb="input"]:focus-within,[data-baseweb="select"]>div:focus-within{border-color:rgba(240,190,116,.6) !important;box-shadow:0 0 0 3px rgba(240,190,116,.15) !important}
button[kind="primary"],button[kind="primaryFormSubmit"]{background:#F0BE74 !important;border:1px solid #F0BE74 !important;color:#1E2A36 !important;font-weight:600 !important;border-radius:11px !important}
button[kind="primary"]:hover,button[kind="primaryFormSubmit"]:hover{background:#F5CD8F !important;border-color:#F5CD8F !important}
button[kind="primary"] p,button[kind="primaryFormSubmit"] p{color:#1E2A36 !important}
button[kind="secondary"],button[kind="secondaryFormSubmit"]{background:rgba(230,225,214,.04) !important;border:1px solid rgba(230,225,214,.18) !important;color:#E6E1D6 !important;border-radius:999px !important}
button[kind="secondary"]:hover,button[kind="secondaryFormSubmit"]:hover{border-color:rgba(240,190,116,.6) !important;background:rgba(240,190,116,.12) !important;color:#E6E1D6 !important}
button:focus-visible{outline:2px solid #F0BE74 !important;outline-offset:3px !important;box-shadow:none !important}
[data-testid="stCaptionContainer"],[data-testid="stCaptionContainer"] p{color:#8C969E !important}
[data-testid="stAlert"]{background:rgba(230,225,214,.05) !important;border:1px solid rgba(230,225,214,.14) !important;border-left:3px solid #F0BE74 !important;border-radius:10px !important}
[data-testid="stAlert"] *{color:#E6E1D6 !important}
.hero .scene{width:min(440px,80vw)}
.hero .wordmark{font-size:clamp(2.6rem,7vw,4.6rem)}
.find h2{font-family:var(--serif);font-weight:300;font-size:clamp(1.6rem,3.6vw,2.4rem);letter-spacing:-.015em;margin:.25rem 0 .4rem;text-align:center;color:#E6E1D6}
.find .intro{text-align:center;margin:0 auto 1rem}
.st-key-go_owner button,.st-key-go_browse button{width:100%;margin-top:-.4rem}
"""


@st.cache_resource
def _build_lock() -> threading.Lock:
    """One build at a time: the invented examples switch the data layer to offline fixtures briefly."""
    return threading.Lock()


def show_html(fragment: str) -> None:
    css = ("<style>" + APP_CSS.split(";", 1)[0] + ";" + browse.standalone_css() + landing.hero_css() + landing.choice_css()
           + APP_CSS.split(";", 1)[1] + "</style>")
    if hasattr(st, "html"):
        st.html(css + fragment)
    else:  # older Streamlit: fall back to an iframe
        import streamlit.components.v1 as components
        components.html("<!doctype html><html><head><meta charset='utf-8'>" + css + "</head><body>" + fragment + "</body></html>",
                        height=2400, scrolling=True)


def _sid() -> str:
    if "sid" not in st.session_state:
        st.session_state.sid = uuid.uuid4().hex[:10]
        st.session_state.homes = []          # [(house_id, label)] for this visitor only
        st.session_state.current = None
        st.session_state.msg = ""
    return st.session_state.sid


def _benchmark(p: Profile) -> None:
    p.set(records.price_benchmark(p, score.config()["price"]), reason="comparable-sales benchmark")
    p.save()


def _remember(p: Profile) -> None:
    label = buyer.address(p).split(",")[0] + (" (example)" if p.synthetic else "")
    homes = [h for h in st.session_state.homes if h[0] != p.house_id]
    st.session_state.homes = [(p.house_id, label)] + homes[:7]
    st.session_state.current = p.house_id


def look_up(address: str) -> Profile:
    with _build_lock():
        p = builder.build(address, house_id=f"browse-{slug(address)[:40]}-{_sid()}")
        builder.apply_answer(p, "stage", "before_buy", reason="looked up in Browse Homes (Streamlit)")
        _benchmark(p)
    return p


def open_example(name: str) -> Profile:
    with _build_lock():
        try:
            addr = samples.install(name)
            p = builder.build(addr, house_id=f"browse-sample-{name}-{_sid()}", mode="offline-sample", synthetic=True)
            builder.apply_answer(p, "stage", "before_buy", reason="example opened in Browse Homes (Streamlit)")
            _benchmark(p)  # from the SYNTHETIC comparable-sales fixtures
        finally:
            hk_http.set_offline(False)
            hk_http.clear_fixtures()
    return p


def choose_candidate(p: Profile, i: int) -> Profile:
    with _build_lock():
        p2 = builder.build(p.address_input, house_id=p.house_id, mode=p.mode, synthetic=p.synthetic, choose=i)
        builder.apply_answer(p2, "stage", "before_buy", reason="property chosen in Browse Homes (Streamlit)")
        _benchmark(p2)
    return p2


# ---------------------------------------------------------------- pages
def nav(context: str) -> None:
    """Compact header with a way back to the home page."""
    c1, c2 = st.columns([5, 1])
    with c1:
        show_html(f'<header class="bar"><span class="mark">Home<span>Keeper</span></span><span class="ctx">{context}</span></header>')
    with c2:
        if st.button("← Home", key="nav_home"):
            st.session_state.view = "home"
            st.session_state.msg = ""
            st.rerun()


def page_home() -> None:
    """The landing page: the lit house, the wordmark, and the two choices."""
    show_html(landing.hero_html())
    c1, c2 = st.columns(2)
    for col, which, label in ((c1, "owner", "I own a home  →"), (c2, "browse", "Browse homes  →")):
        with col:
            show_html(landing.choice_card(which))
            if st.button(label, key="go_" + which, type="primary"):
                st.session_state.view = which
                st.session_state.msg = ""
                st.rerun()
    st.caption("Built from public records and mapped data for Allegheny County, PA. Not an inspection or an appraisal.")


def _owner_html(p: Profile) -> str:
    """The homeowner one-page plan, read-only: no forms, and local-app links turned into plain text."""
    page = web3.house_page(p, snapshot=True)
    page = re.sub(r'<details class="ed">.*?</details>', "", page, flags=re.S)       # inline edit boxes
    page = re.sub(r"<form\b[^>]*>.*?</form>", "", page, flags=re.S)                # answer boxes post to the local server
    return re.sub(r'<a\b([^>]*?)\shref="/[^"]*"([^>]*)>', r'<a\1\2>', page)


def page_owner() -> None:
    nav("Homeowner")
    show_html('<section class="find"><h2>Know what your house needs next.</h2>'
              '<p class="intro">Enter your address in Allegheny County, PA. HomeKeeper pulls the public record and the area&rsquo;s known '
              'risks and lays out what to do first, why, and what it may cost. Online it&rsquo;s a read-only preview: marking work done, '
              'postponing and keeping your records happen in the desktop version.</p></section>')
    with st.form("owner_lookup"):
        c1, c2 = st.columns([5, 1])
        address = c1.text_input("Your address", placeholder="e.g. 123 Main St, Pittsburgh, PA 15228")
        go = c2.form_submit_button("Start", type="primary")
    if st.button("Open the demo house (invented 1928 brick colonial)", key="owner_demo"):
        with _build_lock():
            try:
                addr = samples.install("complete")
                p = builder.build(addr, house_id=f"owner-sample-{_sid()}", mode="offline-sample", synthetic=True)
            finally:
                hk_http.set_offline(False)
                hk_http.clear_fixtures()
        st.session_state.owner = p.house_id
        st.rerun()
    if go:
        if not address.strip():
            st.warning("Type an address first.")
        else:
            with st.spinner("Looking up the public record… this takes a few seconds."):
                try:
                    with _build_lock():
                        p = builder.build(address.strip(), house_id=f"owner-{slug(address)[:40]}-{_sid()}")
                    st.session_state.owner = p.house_id
                except Exception as ex:
                    st.error(f"The lookup didn't finish: {type(ex).__name__}: {ex}")
                    return
            st.rerun()
    hid = st.session_state.get("owner")
    if not hid:
        return
    try:
        p = Profile.load(hid)
    except FileNotFoundError:
        st.session_state.owner = None
        st.info("That house has expired (the app restarted). Please enter it again.")
        return
    stages = {"Under contract to buy it": "under_contract", "I own it": "owner"}
    now = p.value("stage") or "under_contract"
    pick = st.radio("Where are you in the process?", list(stages), index=list(stages.values()).index(now) if now in stages.values() else 0,
                    horizontal=True, key="owner_stage")
    if stages[pick] != now:
        builder.apply_answer(p, "stage", stages[pick], reason="chosen in the online preview")
        st.rerun()
    import streamlit.components.v1 as components
    components.html(_owner_html(p), height=2200, scrolling=True)
    st.caption("Read-only preview. To mark work done, postpone, add equipment or keep documents, use the desktop version (python server.py).")


def page_browse() -> None:
    nav("Browse homes")
    if not st.session_state.current:
        show_html('<section class="find"><h2>What would owning it involve?</h2>'
                  '<p class="intro">Enter the address of a home you&rsquo;re considering in Allegheny County, PA. You&rsquo;ll see the '
                  'property at a glance, an ownership score, any major work the public record points to, the upkeep it asks of an owner, '
                  'and what to settle before you buy. HomeKeeper doesn&rsquo;t list homes for sale, and this isn&rsquo;t an inspection or an appraisal.</p></section>')
    with st.form("lookup"):
        c1, c2 = st.columns([5, 1])
        address = c1.text_input("Address of the home", placeholder="e.g. 123 Main St, Pittsburgh, PA 15228")
        go = c2.form_submit_button("Look up", type="primary")
    if go:
        if not address.strip():
            st.warning("Type an address first.")
        else:
            with st.spinner("Looking up the public record… this takes a few seconds."):
                try:
                    _remember(look_up(address.strip()))
                    st.session_state.msg = ""
                except Exception as ex:  # keep the app up and say what failed
                    st.error(f"The lookup didn't finish: {type(ex).__name__}: {ex}")
                    return
            st.rerun()

    e1, e2, _ = st.columns([1, 1, 2])
    for col, (name, label) in zip((e1, e2), EXAMPLES.items()):
        if col.button(label, help="Invented address and records, for trying the app"):
            _remember(open_example(name))
            st.session_state.msg = "An invented example: the address, its records and its sales don't exist."
            st.rerun()

    if len(st.session_state.homes) > 1:
        ids = [h[0] for h in st.session_state.homes]
        labels = {h[0]: h[1] for h in st.session_state.homes}
        cur = st.session_state.current if st.session_state.current in ids else ids[0]
        pick = st.radio("Looked up", ids, index=ids.index(cur), format_func=lambda i: labels[i], horizontal=True)
        if pick != cur:
            st.session_state.current = pick
            st.session_state.msg = ""
            st.rerun()

    hid = st.session_state.current
    if not hid:
        st.caption("Built from public records and mapped data for Allegheny County. Verify anything that matters with the seller, "
                   "your inspector and the municipality.")
        return

    try:
        p = Profile.load(hid)
    except FileNotFoundError:  # the server restarted and its temporary files are gone
        st.session_state.homes = [h for h in st.session_state.homes if h[0] != hid]
        st.session_state.current = None
        st.info("That lookup has expired (the app restarted). Please look it up again.")
        return

    if st.session_state.msg:
        st.info(st.session_state.msg)

    cands = (p.match or {}).get("candidates") or []
    if not cands:
        st.warning("This address couldn't be matched to a county parcel, or the county's address service didn't answer. "
                   "Check the spelling, include the ZIP code, and try again.")
    elif (p.match or {}).get("ambiguous"):
        st.warning("This address matched more than one property. Choose the one you mean:")
        i = st.radio("Matches", list(range(len(cands))),
                     format_func=lambda k: str(cands[k].get("address") if isinstance(cands[k], dict) else cands[k]))
        if st.button("Use this property"):
            _remember(choose_candidate(p, int(i)))
            st.rerun()

    # The buyer's own inputs to the Ownership Score (labelled as theirs in the score panel).
    ask = p.value("asking_price")
    hoa_now = p.value("hoa_exterior") or "unknown"
    with st.form("inputs"):
        st.markdown("**Your inputs to the Ownership Score**")
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        raw_price = c1.text_input("Asking price (you provide)", value=f"{int(ask):,}" if ask else "", placeholder="e.g. 345,000")
        hoa_label = c2.selectbox("Association handles exterior upkeep?", list(HOA_CHOICES),
                                 index=list(HOA_CHOICES.values()).index(hoa_now))
        update = c3.form_submit_button("Update score", type="primary")
        clear = c4.form_submit_button("Clear price")
    if update or clear:
        try:
            price = None if clear else score.parse_price(raw_price)
        except ValueError:
            st.session_state.msg = f"Couldn't read {raw_price!r} as a price. Try a number like 345000."
            st.rerun()
        before = score.compute(p)["overall"]
        score.set_inputs(p, asking_price=price, hoa_exterior=HOA_CHOICES[hoa_label], clear_price=clear)
        p.save()
        after = score.compute(p)["overall"]
        fmt = lambda v: str(v) if v is not None else "withheld"
        st.session_state.msg = (f"Score updated: {fmt(after)}" + (f" (was {fmt(before)})." if before != after else ", unchanged."))
        st.rerun()

    show_html(browse.property_article(p, interactive=False))
    st.caption("HomeKeeper prototype. Built from public records and mapped data for Allegheny County; the Ownership Score's weights "
               "and thresholds are prototype assumptions, not validated measures. Not an inspection, an appraisal or advice to buy.")


# ---------------------------------------------------------------- run
_sid()
if "view" not in st.session_state:
    st.session_state.view = "home"
{"home": page_home, "browse": page_browse, "owner": page_owner}[st.session_state.view]()
