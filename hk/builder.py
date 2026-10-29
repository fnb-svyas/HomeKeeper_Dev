"""Address -> Profile orchestration.

Pipeline (section 4A of the brief):
  address -> geocode (candidates, ambiguity) -> parcel match -> public records
  -> environmental overlays -> municipal transaction rule -> provisional plan
  -> confirmation questions (only those that could change a recommendation).

Nothing here guesses. A failed or ambiguous step is written into the profile as
an unknown Field or an unresolved match, and the questions list makes it visible.
"""
from __future__ import annotations

import re
from typing import Optional

from . import geocode, overlays, records, municipal
from .evidence import Field, Profile, slug, today, unknown


def _zip_from(address: str, cand: Optional[geocode.Candidate]) -> Optional[str]:
    for text in ((cand.address if cand else ""), address):
        m = re.search(r"\b(15\d{3})\b", text or "")
        if m:
            return m.group(1)
    return None


def build(address: str, *, house_id: Optional[str] = None, mode: str = "live",
          synthetic: bool = False, choose: Optional[int] = None) -> Profile:
    p = Profile(house_id=house_id or slug(address), address_input=address, mode=mode, synthetic=synthetic)
    p.log.append({"date": today(), "event": "build started", "mode": mode})

    # 1. geocode
    m = geocode.geocode(address)
    if choose is not None and m.candidates and 0 <= choose < len(m.candidates):
        m.chosen, m.ambiguous, m.reason = choose, False, f"owner chose candidate {choose}"
    p.match = {"input": m.input, "candidates": m.candidates, "chosen": m.chosen, "ambiguous": m.ambiguous,
               "reason": m.reason, "source_id": m.source_id, "retrieved": m.retrieved,
               "from_fixture": m.from_fixture, "owner_confirmed": choose is not None}
    best = m.best()
    if best is None:
        p.fields["parcel_id"] = unknown("parcel_id", note=f"address match unresolved: {m.reason}").to_dict()
        p.log.append({"date": today(), "event": "match unresolved", "reason": m.reason})
        return _finish(p)

    p.set(Field(name="matched_address", value=best.address, source_id=best.source_id,
                source_ref=f"candidate score {best.score:.0f}, type {best.addr_type}", retrieved_date=m.retrieved,
                evidence_type="public_record", verification_status="unverified"))
    p.set(Field(name="coordinates", value={"lat": best.lat, "lon": best.lon}, source_id=best.source_id,
                source_ref="geocoder location (WGS84)", retrieved_date=m.retrieved,
                evidence_type="public_record", verification_status="unverified",
                limitations="Point-address match" if "Point" in (best.addr_type or "") else
                            "Interpolated along the street segment; may sit on the wrong parcel"))

    # 2. public records
    if best.parcel_id:
        rec, r = records.assessment_by_parid(best.parcel_id)
        if rec:
            for f in records.fields_from_assessment(rec, r.retrieved, "WPRDC Allegheny County Property Assessments"):
                p.set(f)
            muni = p.value("municipality")
            if records.is_city_of_pittsburgh(muni):
                permits, pr = records.permits_by_parcel(best.parcel_id)
                p.set(Field(name="city_permits_since_2019", value=permits if pr.ok else None,
                            source_id="pgh_pli_permits", source_ref=f"PLI permits, parcel_num={best.parcel_id}",
                            retrieved_date=pr.retrieved, evidence_type="public_record" if pr.ok else "unknown",
                            verification_status="unverified" if pr.ok else "unknown",
                            limitations="City of Pittsburgh permits from June 2019 only; plumbing permits excluded; CC-BY City of Pittsburgh.",
                            note="" if pr.ok else f"permit lookup failed: {pr.reason}"))
            else:
                p.set(unknown("city_permits_since_2019",
                              note="Outside the City of Pittsburgh: no consolidated permit data; ask the municipality or rely on the inspection report."))
        else:
            p.set(Field(name="parcel_id", value=best.parcel_id, source_id=best.source_id,
                        source_ref="geocoder PARCELID", evidence_type="public_record", verification_status="unverified"))
            for name in ("year_built", "basement", "roof_type", "heating_cooling", "fireplaces", "municipality"):
                p.set(unknown(name, note=f"assessor record not retrieved: {r.reason}"))
    else:
        for name in ("parcel_id", "year_built", "basement", "roof_type", "heating_cooling", "fireplaces", "municipality"):
            p.set(unknown(name, note="no parcel ID from the geocoder"))

    # 3. overlays (regional exposure)
    z = _zip_from(address, best)
    p.set(overlays.radon_zip_stats(z) if z else unknown("radon_zip_stats", note="no ZIP in address"), overlay=True)
    p.set(overlays.flood_zone(best.lat, best.lon), overlay=True)
    p.set(overlays.undermined(best.lat, best.lon), overlay=True)
    p.set(overlays.landslide_prone(best.lat, best.lon), overlay=True)
    p.set(overlays.soil_map_unit(best.lat, best.lon), overlay=True)
    p.set(overlays.climate_normals(), overlay=True)

    # 4. municipal transaction rule
    p.set(municipal.dye_test_rule(p.value("municipality")), overlay=True)
    # 5. stage: the pilot customer is under contract; the owner can change it (answer <id> stage owner)
    p.set(Field(name="stage", value="under_contract", source_id="owner", source_ref="pilot default; change with 'answer <id> stage owner'",
                evidence_type="owner_reported", verification_status="unverified",
                note="Set to 'owner' after closing; before-you-buy items then retire."))
    return _finish(p)


def _finish(p: Profile) -> Profile:
    p.log.append({"date": today(), "event": "build finished"})
    p.save()
    return p


def apply_answer(p: Profile, field_name: str, value, *, reason: str = "owner answered onboarding question") -> None:
    """Record an owner answer with provenance; None means 'owner says unknown/none' and stays unknown but logged."""
    if field_name == "owner_confirms_match":
        p.match["owner_confirmed"] = bool(value)
        p.log.append({"date": today(), "event": "match confirmed" if value else "match rejected"})
        p.save(); return
    if value is None:
        f = p.get(field_name)
        f.note = (f.note + " | " if f.note else "") + f"owner reports none/unknown on {today()}"
        store = p.overlays if field_name in p.overlays else p.fields
        store[field_name] = f.to_dict()
        p.log.append({"date": today(), "field": field_name, "value": None, "source": "owner", "reason": "owner reports unknown"})
        p.save(); return
    p.correct(field_name, value, reason=reason, status="owner_corrected" if not p.get(field_name).is_unknown else "owner_confirmed")
    p.save()
