"""Municipality-specific transaction rules (hand-curated; data/municipal_dye_tests.json)."""
from __future__ import annotations

import json
import re
from functools import lru_cache

from . import DATA
from .evidence import Field


@lru_cache(maxsize=1)
def _table() -> dict:
    return json.loads((DATA / "municipal_dye_tests.json").read_text(encoding="utf-8"))


def normalize_municipality(munidesc: str | None) -> str | None:
    """'19th Ward - PITTSBURGH' -> 'pittsburgh'; 'Mt. Lebanon' -> 'mt. lebanon'; 'Scott Twp' -> 'scott'."""
    if not munidesc:
        return None
    m = munidesc.strip().lower()
    if "pittsburgh" in m and ("ward" in m or m == "pittsburgh"):
        return "pittsburgh"
    m = re.sub(r"\b(township|twp|borough|boro|municipality of|city of)\b", "", m)
    m = re.sub(r"\s+", " ", m).strip(" -")
    return m or None


def dye_test_rule(munidesc: str | None) -> Field:
    t = _table()
    key = normalize_municipality(munidesc)
    if not key:
        return Field(name="point_of_sale_sewer_rule", value=None,
                     note="municipality unknown — cannot look up point-of-sale sewer requirements")
    entry = t["municipalities"].get(key)
    if not entry:
        return Field(name="point_of_sale_sewer_rule", value={"municipality": munidesc, "known": False},
                     source_id="municipal_dye_tests", source_ref="data/municipal_dye_tests.json (no entry)",
                     evidence_type="unknown", verification_status="unknown",
                     note=(f"No compiled entry for '{munidesc}'. Many Allegheny County municipalities require a "
                           "point-of-sale dye test or lateral inspection; ask the municipality or your agent before "
                           "the closing timeline is fixed."))
    val = dict(entry)
    val["known"] = True
    val["last_checked"] = t["last_checked"]
    return Field(name="point_of_sale_sewer_rule", value=val, source_id="municipal_dye_tests",
                 source_ref=f"{entry['source_note']} — {entry['source_url']}",
                 observed_date=t["last_checked"], evidence_type="public_record", verification_status="unverified",
                 limitations=(f"Compiled from the municipality's own page/code on {t['last_checked']}; fees, lead "
                              "times and validity change. Verify with the municipality."))
