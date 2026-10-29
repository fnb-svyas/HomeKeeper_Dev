"""Address -> candidate matches (parcel ID + coordinates).

Primary: Allegheny County AddressVerification geocoder (live-verified in the audit).
  Returns candidates with score, PointAddress type, PARCELID, municipality info.
Fallback: US Census geocoder (interpolated; no parcel ID) -> then county parcel
  point-in-polygon to recover a PIN.

Ambiguity policy: if the best candidate's score is below 90, or two candidates are
within 5 points of each other, the match is flagged `ambiguous` and the caller must
show the candidates and let the user choose. We never silently pick.
"""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field

from . import http

COUNTY_GEOCODER = ("https://gisdata.alleghenycounty.us/arcgis/rest/services/Geocoders/"
                   "AddressVerification/GeocodeServer/findAddressCandidates")
COUNTY_PARCELS = ("https://gisdata.alleghenycounty.us/arcgis/rest/services/LandRecords/"
                  "Parcel_Features/MapServer/0/query")
CENSUS = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


@dataclass
class Candidate:
    address: str
    lat: float
    lon: float
    score: float
    parcel_id: str | None
    addr_type: str = ""
    municipality: str | None = None
    source_id: str = "county_geocoder"
    raw: dict = field(default_factory=dict)


@dataclass
class Match:
    input: str
    candidates: list            # list[Candidate as dict]
    chosen: int | None          # index into candidates, None if ambiguous/unresolved
    ambiguous: bool
    reason: str
    source_id: str
    retrieved: str | None = None
    from_fixture: bool = False

    def best(self) -> Candidate | None:
        if self.chosen is None:
            return None
        return Candidate(**self.candidates[self.chosen])


def _county_candidates(address: str) -> tuple[list[Candidate], http.FetchResult]:
    url = http.q(COUNTY_GEOCODER, {"SingleLine": address, "outSR": "4326", "maxLocations": "5",
                                   "outFields": "*", "f": "json"})
    r = http.fetch(url)
    out: list[Candidate] = []
    if r.ok and isinstance(r.data, dict):
        for c in r.data.get("candidates", []):
            a = c.get("attributes", {}) or {}
            loc = c.get("location", {}) or {}
            out.append(Candidate(
                address=c.get("address", ""), lat=float(loc.get("y", 0)), lon=float(loc.get("x", 0)),
                score=float(c.get("score", 0)), parcel_id=(a.get("PARCELID") or None),
                addr_type=a.get("Addr_type", ""), municipality=a.get("MUNICIPALITY") or a.get("ZIP_CITY"),
                raw={k: a.get(k) for k in ("PARCELID", "SCHOOLDISTRICT", "ZIP_CITY", "Addr_type", "MUNICIPALITY")}))
    return out, r


def _census_candidates(address: str) -> tuple[list[Candidate], http.FetchResult]:
    url = http.q(CENSUS, {"address": address, "benchmark": "Public_AR_Current", "format": "json"})
    r = http.fetch(url)
    out: list[Candidate] = []
    if r.ok and isinstance(r.data, dict):
        for m in r.data.get("result", {}).get("addressMatches", []):
            xy = m.get("coordinates", {})
            out.append(Candidate(address=m.get("matchedAddress", ""), lat=float(xy.get("y", 0)),
                                 lon=float(xy.get("x", 0)), score=80.0, parcel_id=None,
                                 addr_type="StreetRange (interpolated)", source_id="census_geocoder",
                                 raw={"tigerLineId": m.get("tigerLine", {}).get("tigerLineId")}))
    return out, r


def parcel_from_point(lat: float, lon: float) -> tuple[str | None, http.FetchResult]:
    url = http.q(COUNTY_PARCELS, {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
                                  "inSR": "4326", "spatialRel": "esriSpatialRelWithin",
                                  "outFields": "PIN,MUNICODE", "returnGeometry": "false", "f": "json"})
    r = http.fetch(url)
    if r.ok and isinstance(r.data, dict):
        feats = r.data.get("features", [])
        if feats:
            return feats[0].get("attributes", {}).get("PIN"), r
    return None, r


def geocode(address: str) -> Match:
    cands, r = _county_candidates(address)
    src = "county_geocoder"
    if not cands:
        cands, r2 = _census_candidates(address)
        src = "census_geocoder"
        for c in cands:
            pin, _ = parcel_from_point(c.lat, c.lon)
            c.parcel_id = pin
        if not cands:
            return Match(address, [], None, True,
                         f"no candidates (county: {r.reason or 'none'}; census: {r2.reason or 'none'})",
                         src, None)
        r = r2
    cands.sort(key=lambda c: -c.score)
    best = cands[0]
    ambiguous = False
    reason = f"best candidate score {best.score:.0f} ({best.addr_type or 'n/a'})"
    if best.score < 90:
        ambiguous, reason = True, f"low match score {best.score:.0f} — confirm the address"
    elif len(cands) > 1 and cands[1].score >= best.score - 5 and cands[1].address != best.address:
        ambiguous, reason = True, "two candidates score about equally — choose one"
    elif not best.parcel_id:
        ambiguous, reason = True, "matched a location but no parcel ID — confirm the parcel"
    return Match(address, [c.__dict__ for c in cands], None if ambiguous else 0, ambiguous, reason,
                 src, r.retrieved, r.from_fixture)
