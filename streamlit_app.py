"""HomeKeeper — Browse Homes with the Ownership Score, as a Streamlit app.

Run locally:   streamlit run streamlit_app.py
Deploy:        Streamlit Community Cloud -> New app -> this repository -> main file: streamlit_app.py

This public version covers Browse Homes only (public-record data, no homeowner records).
Each visitor's lookups and asking prices are kept under their own session id on the server's
disk; they are temporary and disappear when the app restarts. The homeowner side stays in the
local app (python server.py).
"""
from __future__ import annotations

import pathlib
import sys
import threading
import uuid

import streamlit as st

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from hk import browse, buyer, builder, http as hk_http, records, samples, score  # noqa: E402
from hk.evidence import Profile, slug  # noqa: E402

st.set_page_config(page_title="HomeKeeper — Browse homes", page_icon="🏠", layout="wide")

EXAMPLES = {"complete": "Example: 1928 brick colonial", "missing": "Example: sparse city record"}
HOA_CHOICES = {"Not known": "unknown", "No": "no", "Yes": "yes"}

# Streamlit's own layout, nudged to match the HomeKeeper dusk theme (colours are in .streamlit/config.toml).
APP_CSS = """
body::before{display:none}
.block-container,[data-testid="stMainBlockContainer"]{max-width:1080px;padding-top:1.5rem}
.find{padding:.5rem 0 .25rem}
"""


@st.cache_resource
def _build_lock() -> threading.Lock:
    """One build at a time: the invented examples switch the data layer to offline fixtures briefly."""
    return threading.Lock()


def show_html(fragment: str) -> None:
    css = "<style>" + browse.standalone_css() + APP_CSS + "</style>"
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


# ---------------------------------------------------------------- page
_sid()
show_html(
    '<header class="bar"><span class="mark">Home<span>Keeper</span></span><span class="ctx">Browse homes</span></header>'
    '<section class="find"><h1>What would owning it involve?</h1>'
    '<p class="intro">Enter the address of a home you&rsquo;re considering in Allegheny County, PA. You&rsquo;ll see the property at a glance, '
    'an ownership score, any major work the public record points to, the upkeep it asks of an owner, and what to settle before you buy. '
    'HomeKeeper doesn&rsquo;t list homes for sale, and this isn&rsquo;t an inspection or an appraisal.</p></section>')

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
                st.stop()
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
    st.stop()

try:
    p = Profile.load(hid)
except FileNotFoundError:  # the server restarted and its temporary files are gone
    st.session_state.homes = [h for h in st.session_state.homes if h[0] != hid]
    st.session_state.current = None
    st.info("That lookup has expired (the app restarted). Please look it up again.")
    st.stop()

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
