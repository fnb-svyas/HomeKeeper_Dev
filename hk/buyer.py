"""Buyer's overview for Browse Homes: what owning this house would involve.

Built only from the public record, mapped regional data and the hand-compiled municipal table
stored on a browse profile. It never reads documents, completions, history or quotes from a
homeowner's record, and it never turns the construction year into a claim about the roof (or any
other component) needing work.

Four parts:
  glance     - basic facts that explain ownership demands; missing ones stay "Not recorded"
  major      - substantial projects, each only when a specific piece of evidence supports it,
               labelled documented need / planning consideration / needs assessment
  ownership  - short plain-language themes (exterior, site, basement, weather, insurance/shared)
  unknowns   - the few unanswered questions that could change the ownership picture
"""
from __future__ import annotations

import datetime as _dt
import json
from functools import lru_cache
from typing import Optional

from . import DATA, sources
from .evidence import Field, Profile

STATUS = {
    "documented": "Documented need",
    "planning": "Planning consideration",
    "assess": "Needs assessment",
}

NOT_RECORDED = "Not recorded"
_CLOSED_PERMIT = ("final", "complete", "closed")
_ATTACHED = ("TOWNHOUSE", "ROW", "CONDO", "TWO FAMILY", "THREE FAMILY", "DUPLEX", "APART")


@lru_cache(maxsize=1)
def _rules() -> dict:
    d = json.loads((DATA / "rules.json").read_text(encoding="utf-8"))
    return {r["id"]: r for r in d["rules"]}


def _year() -> int:
    return _dt.date.today().year


def _src_name(source_id: Optional[str]) -> str:
    if not source_id:
        return ""
    try:
        s = sources.get(source_id)
        return f"{s['publisher']} — {s['name']}"
    except KeyError:
        return source_id


def _ev(f: Field, said: str) -> dict:
    """One evidence line: what the source says, where it came from, and its limits."""
    return {"said": said, "source": _src_name(f.source_id), "ref": f.source_ref,
            "retrieved": f.retrieved_date or "", "limits": f.limitations or f.note or ""}


def _rule_ev(rule_id: str, said: str) -> dict:
    r = _rules().get(rule_id, {})
    return {"said": said, "source": _src_name(r.get("source_id")), "ref": r.get("source_ref", ""),
            "retrieved": r.get("review_date", ""), "limits": "Rule text is author-reviewed, not expert-validated."}


def _public(p: Profile, name: str) -> Field:
    """A field only if it came from a public or mapped source (never an owner's private entry)."""
    f = p.get(name)
    if f.is_unknown or f.evidence_type not in ("public_record", "regional_exposure"):
        return Field(name=name, value=None, note=f.note)
    return f


def _pv(p: Profile, name: str):
    f = _public(p, name)
    return None if f.is_unknown else f.value


def _title(s: Optional[str]) -> Optional[str]:
    if not s:
        return s
    small = {"and", "or", "with", "of", "the"}
    words = str(s).replace("_", " ").split()
    return " ".join(w.lower() if (i and w.lower() in small) else (w if any(c.isdigit() for c in w) else w.capitalize()) for i, w in enumerate(words))


def _num(n) -> str:
    return f"{int(n):,}"


def address(p: Profile) -> str:
    m = p.get("matched_address")
    a = m.value if not m.is_unknown else p.address_input
    parts = [x.strip() for x in str(a).split(",")]
    out = []
    for x in parts:
        out.append(x if any(c.isdigit() for c in x) and len(x) <= 6 else _title(x) if x.isupper() else x)
    return ", ".join(out)


# ---------------------------------------------------------------- permits
def _permits(p: Profile) -> list[dict]:
    v = _pv(p, "city_permits_since_2019")
    return v if isinstance(v, list) else []


def _roof_permits(p: Profile) -> list[dict]:
    out = []
    for r in _permits(p):
        text = " ".join(str(r.get(k) or "") for k in ("work_type", "work_description")).lower()
        if "roof" in text:
            out.append(r)
    return out


def _is_closed(r: dict) -> bool:
    return any(w in str(r.get("status") or "").lower() for w in _CLOSED_PERMIT)


# ---------------------------------------------------------------- A. at a glance
def glance(p: Profile) -> dict:
    rows = []

    def row(label, name, fmt=None, extra=""):
        f = _public(p, name)
        val = None if f.is_unknown else (fmt(f.value) if fmt else _title(f.value))
        rows.append({"label": label, "value": val or NOT_RECORDED, "known": bool(val), "field": name,
                     "ev": _ev(f, f"{label}: {val}") if val else None, "extra": extra})

    yb = _pv(p, "year_built")
    row("Built", "year_built", lambda v: f"{v} (about {_year() - int(v)} years)")
    row("Property type", "use_description")
    row("Style", "style")
    row("Stories", "stories", lambda v: f"{v:g}" if isinstance(v, float) else str(v))
    row("Living area", "living_area", lambda v: f"{_num(v)} sq ft")
    row("Lot", "lot_area", lambda v: f"{_num(v)} sq ft")
    bed, bath = _pv(p, "bedrooms"), _pv(p, "full_baths")
    rows.append({"label": "Bedrooms / baths", "known": bool(bed or bath), "field": "bedrooms",
                 "value": (f"{bed or '?'} bed · {bath or '?'} full bath") if (bed or bath) else NOT_RECORDED,
                 "ev": _ev(_public(p, "bedrooms"), "Bedrooms and full baths from the assessor record") if (bed or bath) else None, "extra": ""})
    row("Exterior walls", "exterior_finish")
    row("Roof covering", "roof_type", extra="Covering type only; its age and condition aren't in the record.")
    row("Basement", "basement")
    row("Assessor's condition rating", "condition_assessor",
        extra="A valuation category, not an inspection.")
    row("Municipality", "municipality")

    # site and location characteristics
    site = []
    fz = _public(p, "flood_zone")
    if not fz.is_unknown and isinstance(fz.value, dict):
        z = fz.value.get("fld_zone")
        if fz.value.get("sfha"):
            site.append({"text": f"In FEMA's mapped high-risk flood area (zone {z})", "flag": True, "ev": _ev(fz, f"FEMA flood zone {z}, special flood hazard area")})
        elif z:
            site.append({"text": f"Outside FEMA's high-risk flood area (zone {z})", "flag": False, "ev": _ev(fz, f"FEMA flood zone {z}")})
    else:
        site.append({"text": "Flood zone: not retrieved", "flag": None, "ev": None})
    um = _public(p, "undermined")
    if um.value is True:
        site.append({"text": "In an area DEP lists as undermined by coal mining", "flag": True, "ev": _ev(um, "Inside DEP's confirmed-mining layer")})
    elif um.value is False:
        site.append({"text": "Not in DEP's confirmed-mining layer", "flag": False, "ev": _ev(um, "Outside DEP's confirmed-mining layer")})
    ls = _public(p, "landslide_prone")
    if ls.value is True:
        site.append({"text": "In the county's landslide-prone area", "flag": True, "ev": _ev(ls, "Inside the county landslide-prone layer")})
    soil = _public(p, "soil_map_unit")
    if not soil.is_unknown and isinstance(soil.value, dict) and soil.value.get("drainagecl"):
        dc = soil.value["drainagecl"]
        site.append({"text": f"Mapped soil: {dc.lower()}", "flag": "poorly" in dc.lower(),
                     "ev": _ev(soil, f"{soil.value.get('muname')}: {dc}")})
    return {"rows": rows, "site": site, "year_built": yb}


# ---------------------------------------------------------------- B. potential major work
def major_work(p: Profile) -> list[dict]:
    items = []
    yb = _pv(p, "year_built")

    # Documented findings recorded on this browse profile (e.g. the buyer's own inspection report).
    for f in p.findings:
        if f.get("status") == "open" and f.get("severity") in ("major", "safety"):
            items.append({"key": "finding-" + f["id"], "title": _title(f["component"]) + ": " + f["description"],
                          "status": "documented",
                          "what": f.get("recommendation") or "Repair as the report recommends.",
                          "evidence": [{"said": f["description"], "source": f.get("source_doc", "inspection report"),
                                        "ref": f.get("location", ""), "retrieved": f.get("recorded", ""), "limits": ""}],
                          "timing": None})

    # Roof: only when its age is established (never from the construction year).
    rt = _pv(p, "roof_type") or ""
    ry = p.get("roof_installed_year")
    if not ry.is_unknown and (not rt or "shingle" in str(rt).lower()):
        age = _year() - int(ry.value)
        if age >= 15:
            items.append({"key": "roof", "title": "Roof replacement budget", "status": "planning",
                          "what": (f"The roof was installed in {ry.value} (about {age} years ago). Asphalt shingle roofs are "
                                   "commonly planned at 20–30 years; condition, not age, decides the actual timing."),
                          "evidence": [_ev(ry, f"Roof installed {ry.value}"),
                                       _rule_ev("R-ROOF-002", "Guideline life: 3-tab ~20 yr, architectural ~30 yr")],
                          "timing": f"Within the guideline window in about {max(0, 20 - age)}–{max(0, 30 - age)} years" if age < 30 else "Past the guideline window; a roofer's assessment decides"})

    # Assessor condition rating at the bottom of the scale.
    cond = _public(p, "condition_assessor")
    if not cond.is_unknown and str(cond.value).upper() in ("POOR", "VERY POOR", "UNSOUND"):
        items.append({"key": "condition", "title": "Broad repair or renovation", "status": "assess",
                      "what": ("The county assessor rates this house's condition as " + _title(cond.value).lower() +
                               ". That is a valuation category, not an inspection, but it suggests substantial work; "
                               "a full inspection should establish what and how much."),
                      "evidence": [_ev(cond, "Assessor condition: " + str(cond.value))], "timing": None})

    # Permitted work with no final inspection on record (City of Pittsburgh parcels).
    for r in _permits(p):
        if not _is_closed(r):
            items.append({"key": "permit-" + str(r.get("permit_id")), "status": "assess",
                          "title": "Unfinished permitted work: " + _title(str(r.get("work_type") or r.get("permit_type") or "work")).lower(),
                          "what": ("A city permit for “" + str(r.get("work_description") or "work") + "” shows status “" +
                                   str(r.get("status") or "unknown") + "”, not finaled. Ask whether the work was completed and inspected."),
                          "evidence": [_ev(_public(p, "city_permits_since_2019"),
                                           f"Permit {r.get('permit_id')} issued {r.get('issue_date')}, status {r.get('status')}")],
                          "timing": "Before closing"})

    # Sewer lateral: the municipality requires a test at sale; repair only if it fails.
    rule = _public(p, "point_of_sale_sewer_rule")
    if not rule.is_unknown and isinstance(rule.value, dict) and rule.value.get("known") and rule.value.get("required_at_sale"):
        v = rule.value
        evs = [_ev(rule, f"{v.get('name')}: certification required at sale; fee {v.get('fee')}; timing: {v.get('lead_time')}; if it fails: {v.get('fail_handling')}")]
        what = (f"{v.get('name')} requires a sewer test or certification before the sale. If the line to the street fails, "
                "repairs (or an escrow agreement) are needed before or at closing.")
        if yb and int(yb) < 1960:
            what += " Lines from this era are commonly clay or cast iron."
            evs.append(_rule_ev("R-SEWER-002", "Pre-1960 laterals commonly clay or cast iron; the owner owns the lateral"))
        items.append({"key": "sewer", "title": "Possible sewer-line repair", "status": "assess", "what": what,
                      "evidence": evs, "timing": "Before closing",
                      "cost_note": f"Municipal fee {v.get('fee')}; repair cost unknown unless the test fails."})

    # Slope and retaining walls.
    ls = _public(p, "landslide_prone")
    if ls.value is True:
        items.append({"key": "slope", "title": "Slope, retaining-wall or drainage work", "status": "assess",
                      "what": ("The lot is in the county's landslide-prone area. Walls that lean or bulge, cracks in the ground, "
                               "or water running onto the slope can mean substantial work; have the inspector look, and get a "
                               "geotechnical or structural opinion if anything is noted."),
                      "evidence": [_ev(ls, "Inside the county landslide-prone layer")], "timing": None})

    # Basement water: poorly drained soil or a high-risk flood zone.
    soil = _public(p, "soil_map_unit")
    poor = (not soil.is_unknown and isinstance(soil.value, dict) and
            "poorly" in str(soil.value.get("drainagecl") or "").lower())
    fz = _public(p, "flood_zone")
    sfha = not fz.is_unknown and isinstance(fz.value, dict) and fz.value.get("sfha")
    if poor or sfha:
        evs = []
        if poor:
            evs.append(_ev(soil, f"Mapped soil drainage: {soil.value.get('drainagecl')}"))
        if sfha:
            evs.append(_ev(fz, f"FEMA zone {fz.value.get('fld_zone')}, special flood hazard area"))
        items.append({"key": "water", "title": "Basement waterproofing or drainage", "status": "assess",
                      "what": ("Mapped conditions here favour water at the foundation. Whether this basement takes water is not "
                               "known; the seller disclosure and the inspection are where that shows up."),
                      "evidence": evs, "timing": None})

    for it in items:
        est = _estimate(p, it["key"])
        it["cost"] = est
    return items


def _estimate(p: Profile, key: str) -> Optional[dict]:
    """A cost range only if one was recorded for this browse profile with a basis and scope."""
    for e in reversed(getattr(p, "estimates", None) or []):
        if e.get("applies_to") == key and e.get("scope") and e.get("basis"):
            return e
    return None


# ---------------------------------------------------------------- C. ownership and upkeep
_EXTERIOR = {
    "brick": "Brick walls need little routine upkeep; on an older house, expect occasional mortar repair (repointing) and watch where water runs down the walls.",
    "stone": "Stone walls are durable; mortar joints need repair from time to time on an older house.",
    "frame": "A frame house has siding or shingles over wood; painted wood needs repainting every several years and any rot repaired. The record doesn't say what the covering is.",
    "stucco": "Stucco needs cracks sealed promptly; water behind it is the expensive problem.",
    "masonry": "Masonry walls need little routine upkeep beyond occasional mortar repair.",
    "log": "Log walls need regular sealing and checking for rot and insects.",
    "concrete": "Concrete block walls need little routine upkeep; watch for cracks and water.",
}


def ownership(p: Profile) -> list[dict]:
    out = []
    yb = _pv(p, "year_built")
    yf = _public(p, "year_built")
    if yb:
        age = _year() - int(yb)
        txt = f"Built around {yb}, about {age} years ago. "
        if int(yb) < 1960:
            txt += ("At this age most systems have been replaced at least once, piece by piece; expect steady updating rather "
                    "than a one-time fix, and ask what has been done and when.")
        elif age >= 25:
            txt += "Original components of this age are reaching the point where replacements come up."
        else:
            txt += "A newer house usually means fewer replacements in the first years."
        out.append({"key": "age", "title": "Age", "text": txt, "evidence": [_ev(yf, f"Year built {yb}")]})
    else:
        out.append({"key": "age", "title": "Age", "evidence": [],
                    "text": "The construction year isn't recorded, so it's hard to judge how much of the house is original."})

    ext = _public(p, "exterior_finish")
    rt = _public(p, "roof_type")
    st = _pv(p, "stories")
    bits = []
    if not ext.is_unknown:
        key = next((k for k in _EXTERIOR if k in str(ext.value).lower()), None)
        bits.append(_EXTERIOR[key] if key else f"Exterior walls are recorded as {str(ext.value).lower()}.")
    else:
        bits.append("The exterior material isn't recorded.")
    if not rt.is_unknown:
        bits.append(f"The roof is recorded as {str(rt.value).lower()}; its age is not.")
    if st and float(st) >= 2:
        bits.append("At two or more stories, gutter, roof and upper-wall work generally needs ladders or a contractor.")
    evs = [x for x in (_ev(ext, f"Exterior: {ext.value}") if not ext.is_unknown else None,
                       _ev(rt, f"Roof covering: {rt.value}") if not rt.is_unknown else None) if x]
    out.append({"key": "exterior", "title": "Exterior", "text": " ".join(bits), "evidence": evs})

    lot = _pv(p, "lot_area")
    ls = _public(p, "landslide_prone")
    site_bits, site_ev = [], []
    if lot:
        size = "small" if lot < 5000 else "modest" if lot < 15000 else "large"
        site_bits.append(f"A {size} lot ({_num(lot)} sq ft): " +
                         {"small": "little yard work.", "modest": "ordinary yard upkeep.",
                          "large": "more mowing, trees and drainage to look after."}[size])
        site_ev.append(_ev(_public(p, "lot_area"), f"Lot area {_num(lot)} sq ft"))
    else:
        site_bits.append("Lot size isn't recorded.")
    if ls.value is True:
        site_bits.append("On a landslide-prone slope, keeping downspouts and runoff off the hillside matters every year.")
        site_ev.append(_ev(ls, "Inside the county landslide-prone layer"))
    out.append({"key": "site", "title": "Yard and site", "text": " ".join(site_bits), "evidence": site_ev})

    bs = _public(p, "basement")
    soil = _public(p, "soil_map_unit")
    b_bits, b_ev = [], []
    if not bs.is_unknown and str(bs.value).lower() in ("full", "part"):
        b_bits.append(f"{_title(bs.value)} basement. In this climate basements tend to run humid in summer; plan on a "
                      "dehumidifier and on keeping gutters and grading working so water stays away from the walls.")
        b_ev.append(_ev(bs, f"Basement: {bs.value}"))
        b_ev.append(_rule_ev("R-BSMT-001", "Keep basement humidity under 60%"))
    elif not bs.is_unknown:
        b_bits.append(f"Basement recorded as {str(bs.value).lower()}.")
        b_ev.append(_ev(bs, f"Basement: {bs.value}"))
    else:
        b_bits.append("Whether there is a basement isn't recorded.")
    if not soil.is_unknown and isinstance(soil.value, dict) and soil.value.get("drainagecl"):
        b_bits.append(f"The mapped soil here is {str(soil.value['drainagecl']).lower()} (an area description, not this lot).")
        b_ev.append(_ev(soil, f"Soil drainage class: {soil.value['drainagecl']}"))
    out.append({"key": "basement", "title": "Basement and moisture", "text": " ".join(b_bits), "evidence": b_ev})

    cn = _public(p, "climate_normals")
    if not cn.is_unknown and isinstance(cn.value, dict):
        v = cn.value
        txt = ("Real winters: about {hdd} heating degree days and {snow} inches of snow a year, with freezes from about "
               "{ff} to {lf}. Heating is a significant running cost, and outdoor pipes, gutters and walks need attention "
               "before and through winter.").format(hdd=_num(v.get("heating_degree_days_base65") or 0), snow=round(v.get("annual_snow_in") or 0),
                                                   ff=_md(v.get("first_freeze_median")), lf=_md(v.get("last_freeze_median")))
        out.append({"key": "weather", "title": "Weather", "text": txt,
                    "evidence": [_ev(cn, "1991–2020 normals at Pittsburgh International Airport")]})

    ins_bits, ins_ev = [], []
    um = _public(p, "undermined")
    if um.value is True:
        ins_bits.append("Homeowners policies usually exclude mine subsidence; the state's Mine Subsidence Insurance is a "
                        "separate yearly cost (DEP cites roughly $0.27 per $1,000 of coverage — confirm the current rate).")
        ins_ev.append(_ev(um, "Inside DEP's confirmed-mining layer"))
        ins_ev.append(_rule_ev("R-MSI-001", "Policy applied for at purchase agreement takes effect at closing"))
    fz = _public(p, "flood_zone")
    if not fz.is_unknown and isinstance(fz.value, dict) and fz.value.get("sfha"):
        ins_bits.append("In a mapped high-risk flood area, a mortgage lender will usually require flood insurance.")
        ins_ev.append(_ev(fz, "FEMA special flood hazard area"))
    use = str(_pv(p, "use_description") or "").upper()
    if any(w in use for w in _ATTACHED):
        ins_bits.append("This property type can share walls, roofs or driveways; who pays for shared exterior work isn't in the public record.")
        ins_ev.append(_ev(_public(p, "use_description"), f"Use: {use.title()}"))
    if p.responsibilities:
        ins_bits.append("Recorded as someone else's responsibility: " + ", ".join(f"{_title(k).lower()} ({v})" for k, v in p.responsibilities.items()) + ".")
    if not ins_bits:
        ins_bits.append("No shared or association responsibility shows in the public record, and no special insurance flag "
                        "came up in the mapped data. Ask the seller whether anything is shared.")
    out.append({"key": "costs", "title": "Insurance and shared costs", "text": " ".join(ins_bits), "evidence": ins_ev})
    return out


def _md(s) -> str:
    try:
        m, d = str(s).split("/")
        return _dt.date(2001, int(m), 1).strftime("%B") + " " + str(int(d))
    except Exception:
        return str(s or "?")


# ---------------------------------------------------------------- D. unknowns
def unknowns(p: Profile) -> list[dict]:
    out = []
    yb = _pv(p, "year_built")
    rt = _pv(p, "roof_type")
    ry = p.get("roof_installed_year")
    rp = _roof_permits(p)
    if ry.is_unknown:
        if rp:
            r = rp[-1]
            out.append({"q": "What exactly was done to the roof?",
                        "why": (f"A city permit for “{str(r.get('work_description') or 'roof work').lower()}” was issued "
                                f"{r.get('issue_date')} (status {str(r.get('status') or 'unknown').lower()}). Ask for the invoice "
                                "and warranty to confirm the scope and date."),
                        "evidence": [_ev(_public(p, "city_permits_since_2019"), f"Permit {r.get('permit_id')}: {r.get('work_description')}")]})
        else:
            cov = f"lists the roof covering ({str(rt).lower()}) but" if rt else "has"
            out.append({"q": "How old is the roof, and what condition is it in?",
                        "why": (f"The public record {cov} no installation date. Ask the seller for roofing invoices; the inspection "
                                "describes condition but won't predict how long it will last."),
                        "evidence": [_rule_ev("R-ROOF-001", "Inspectors are not required to predict roof life")]})
    bs = _pv(p, "basement")
    if bs is None or str(bs).lower() in ("full", "part"):
        out.append({"q": "Has the basement taken water?",
                    "why": ("Pennsylvania's seller disclosure asks about water in the basement; compare it with what the "
                            "inspector sees (staining, efflorescence, a sump that runs)."),
                    "evidence": [_rule_ev("R-DISC-001", "The seller disclosure defines what must be disclosed")]})
    if _pv(p, "undermined") is True or _pv(p, "landslide_prone") is True:
        out.append({"q": "Does the foundation or any retaining wall show movement?",
                    "why": ("The mapped data flags this location, but says nothing about this house. Cracks, sticking doors "
                            "or leaning walls noted in the inspection need a structural opinion before you commit."),
                    "evidence": [x for x in (_ev(_public(p, "undermined"), "Undermined area") if _pv(p, "undermined") else None,
                                             _ev(_public(p, "landslide_prone"), "Landslide-prone area") if _pv(p, "landslide_prone") else None) if x]})
    rule = _public(p, "point_of_sale_sewer_rule")
    if not rule.is_unknown and isinstance(rule.value, dict):
        if rule.value.get("known") and rule.value.get("required_at_sale"):
            out.append({"q": "Who arranges the sewer test, and who pays if it fails?",
                        "why": "Settle this in the agreement of sale; a failed test can hold up closing.",
                        "evidence": [_ev(rule, f"{rule.value.get('name')}: certification required at sale")]})
        elif not rule.value.get("known"):
            out.append({"q": f"Does {_title(rule.value.get('municipality'))} require a sewer test at sale?",
                        "why": "Many Allegheny County municipalities do; ask the municipality or your agent.",
                        "evidence": [_ev(rule, "No compiled entry for this municipality")]})
    if yb is None or int(yb) < 1960:
        out.append({"q": "What wiring and pipe materials does the house have?",
                    "why": ("Houses of this era often still have original wiring or galvanized and cast-iron pipes; the "
                            "public record never says, and replacement is a major cost if they remain." if yb else
                            "The construction year isn't recorded, and the public record never describes wiring or pipes."),
                    "evidence": [_rule_ev("R-ELEC-001", "Original wiring common in pre-1960 houses"),
                                 _rule_ev("R-PLUMB-001", "Galvanized supply and cast-iron drains common in pre-1960 houses")]})
    if _pv(p, "undermined") is True:
        out.append({"q": "Will you buy mine subsidence insurance?",
                    "why": "Apply at the agreement of sale so cover starts at closing.",
                    "evidence": [_rule_ev("R-MSI-001", "Coverage effective at closing when applied for at purchase agreement")]})
    rz = _public(p, "radon_zip_stats")
    if not rz.is_unknown and isinstance(rz.value, dict):
        v = rz.value
        out.append({"q": "What is this house's radon level?",
                    "why": (f"In ZIP {v.get('zip')}, {v.get('pct_at_or_above_4')}% of {v.get('tests')} reported tests were at or above "
                            "EPA's 4 pCi/L action level. Only a test in this house tells you; mitigation, if needed, is a "
                            "known, contained cost."),
                    "evidence": [_ev(rz, f"{v.get('tests')} DEP tests in ZIP {v.get('zip')}, median {v.get('median_pci_l')} pCi/L")]})
    use = str(_pv(p, "use_description") or "").upper()
    if any(w in use for w in _ATTACHED):
        out.append({"q": "Who is responsible for shared walls, roof or driveway?",
                    "why": "Shared exterior work can be split, assigned to an association, or simply unclear.",
                    "evidence": [_ev(_public(p, "use_description"), f"Use: {use.title()}")]})
    return out


# ---------------------------------------------------------------- the whole picture
def summary_line(p: Profile, g: dict, major: list, unk: list) -> str:
    """One sentence answering 'what would owning this house involve?' from the facts on hand."""
    desc = []
    yb = g.get("year_built")
    if yb:
        desc.append(f"A {yb}")
    ext = _pv(p, "exterior_finish")
    if ext:
        desc.append(str(ext).lower())
    sty = _pv(p, "style")
    desc.append(str(sty).lower() if sty else "house")
    bs = _pv(p, "basement")
    head = (" ".join(desc) if yb else "A " + " ".join(desc)) + (f" with a {str(bs).lower()} basement" if bs and str(bs).lower() in ("full", "part") else "")
    n = len(major)
    if n:
        tail = f"The record points to {n} potential major {'project' if n == 1 else 'projects'} to look into"
    else:
        tail = "The record doesn't establish any major project"
    tail += f", and leaves {min(len(unk), 5)} important {'question' if min(len(unk), 5) == 1 else 'questions'} for before you buy."
    return head + ". " + tail


def overview(p: Profile) -> dict:
    g = glance(p)
    m = major_work(p)
    o = ownership(p)
    u = unknowns(p)
    return {"address": address(p), "glance": g, "major": m, "ownership": o, "unknowns": u,
            "summary": summary_line(p, g, m, u), "synthetic": p.synthetic,
            "retrieved": p.get("matched_address").retrieved_date or p.created,
            "match": p.match}
