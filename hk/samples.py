"""SYNTHETIC fixtures for offline demonstrations and tests.

Nothing here is real property data. The addresses do not exist, the parcel IDs are
made up, and the response payloads only imitate the *shape* of each API so the
pipeline can be exercised without the network. Profiles built from these carry
synthetic=True and the house_id prefix "sample-".
"""
from __future__ import annotations

import json

from . import DATA, http, geocode, records, overlays

SAMPLES = {
    "complete": "123 Sample St, Pittsburgh, PA 15228",     # pretend Mt. Lebanon, 1928 brick, full basement
    "missing": "456 Placeholder Ave, Pittsburgh, PA 15210",  # pretend City 18th Ward, sparse assessor record
    "ambiguous": "100 Main St, Pittsburgh",                 # two equally scored candidates
}


def _geocoder_url(address):
    return http.q(geocode.COUNTY_GEOCODER, {"SingleLine": address, "outSR": "4326", "maxLocations": "5",
                                            "outFields": "*", "f": "json"})


def _assess_url(parid):
    return http.q(records.WPRDC_API, {"resource_id": records.ASSESSMENTS_RESOURCE,
                                      "filters": json.dumps({"PARID": parid}), "limit": "2"})


def _permits_url(parid):
    return http.q(records.WPRDC_API, {"resource_id": records.PERMITS_RESOURCE,
                                      "filters": json.dumps({"parcel_num": parid}), "limit": "50"})


def _cand(address, lat, lon, score, parcelid, addr_type="PointAddress", muni=None):
    return {"address": address, "location": {"x": lon, "y": lat}, "score": score,
            "attributes": {"PARCELID": parcelid, "Addr_type": addr_type, "ZIP_CITY": muni or "PITTSBURGH",
                           "SCHOOLDISTRICT": "SYNTHETIC SD", "MUNICIPALITY": muni}}


def _ckan(records_):
    return {"success": True, "result": {"records": records_, "total": len(records_),
                                        "fields": [{"id": k} for k in (records_[0].keys() if records_ else [])]}}


def _common_overlays(lat, lon, *, undermined=False, landslide=False, flood=True):
    http.register_fixture("GET", http.q(overlays.RADON, {"$select": "measure_value,test_end_date,test_floor_level_text,mitigation_system_indicator",
                                                           "$where": "address_postal_code='15228' AND county_name='Allegheny'",
                                                           "$limit": "50000"}),
                          [{"measure_value": v, "test_end_date": "2025-03-0%dT00:00:00.000" % (i % 9 + 1),
                            "test_floor_level_text": "BASEMENT", "mitigation_system_indicator": "NOT COLLECTED"}
                           for i, v in enumerate(["1.2", "3.9", "6.5", "2.1", "0.8", "11.0", "4.4", "2.7", "5.1", "1.9", "3.3", "7.8"])])
    http.register_fixture("GET", http.q(overlays.RADON, {"$select": "measure_value,test_end_date,test_floor_level_text,mitigation_system_indicator",
                                                           "$where": "address_postal_code='15210' AND county_name='Allegheny'",
                                                           "$limit": "50000"}),
                          [{"measure_value": v, "test_end_date": "2024-11-01T00:00:00.000",
                            "test_floor_level_text": "BASEMENT", "mitigation_system_indicator": "NOT COLLECTED"}
                           for v in ["2.0", "5.6", "9.1", "1.1", "3.8"]])
    if flood:
        http.register_fixture("GET", f"{overlays.NFHL}/28/query?geometry={lon},{lat}",
                              {"features": [{"attributes": {"FLD_ZONE": "X", "ZONE_SUBTY": "AREA OF MINIMAL FLOOD HAZARD",
                                                             "SFHA_TF": "F", "STATIC_BFE": -9999}}]})
    http.register_fixture("GET", f"{overlays.MSI}?geometry={lon},{lat}",
                          {"features": [{"attributes": {"ID": 0}}] if undermined else []})
    http.register_fixture("GET", f"{overlays.PASDA_AC}/{overlays.LANDSLIDE_LAYER}/query?geometry={lon},{lat}",
                          {"features": [{"attributes": {"landslidep": "Yes"}}] if landslide else []})
    http.register_fixture("POST", overlays.SDA,
                          {"Table": [["mukey", "muname", "compname", "comppct_r", "drainagecl", "hydricrating", "frostact",
                                      "corcon", "corsteel", "wtdepannmin", "drclassdcd", "flodfreqdcd"],
                                     ["999001", "Synthetic silt loam, 8 to 15 percent slopes", "Synthetic", "85",
                                      "Moderately well drained", "No", "Moderate", "Moderate", "High", "61", "Moderately well drained", "None"]]})
    http.register_fixture("GET", overlays.NCEI,
                          [{"STATION": "USW00094823", "ANN-HTDD-NORMAL": "5710", "ANN-SNOW-NORMAL": "414",
                            "ANN-TMIN-PRBLST-T32FP50": "04/24", "ANN-PRCP-NORMAL": "3819", "ANN-TMIN-PRBFST-T32FP50": "10/20"}])


def _comps(scope, value, use, area, sales, *, bad_price=False):
    """Register a SYNTHETIC comparable-sales response: (months ago, sq ft, $ per sq ft, year built)."""
    import datetime as _dt
    cfg = json.loads((DATA / "score_config.json").read_text(encoding="utf-8"))["price"]
    lo, hi = records.size_band(area, cfg["size_tolerance"])
    today = _dt.date.today()
    rows = []
    for i, (months, sq, ppsf, yb) in enumerate(sales):
        d = today - _dt.timedelta(days=int(months * 30.44))
        rows.append({"PARID": f"SYNCOMP{i:09d}", "SALEPRICE": float(sq * ppsf), "SALEDATE": d.strftime("%m-%d-%Y"),
                     "SALEDESC": "VALID SALE", "FINISHEDLIVINGAREA": sq, "YEARBLT": str(yb or ""), "USEDESC": use,
                     "NEIGHCODE": value if scope == "neighborhood" else "", "MUNIDESC": value if scope == "municipality" else ""})
    if bad_price:
        rows.append({"PARID": "SYNCOMP999999999", "SALEPRICE": 1.0, "SALEDATE": today.strftime("%m-%d-%Y"), "SALEDESC": "VALID SALE",
                     "FINISHEDLIVINGAREA": 1800, "YEARBLT": "1930", "USEDESC": use, "NEIGHCODE": value, "MUNIDESC": ""})
    http.register_fixture("GET", records.comps_url(scope, value, use, lo, hi), _ckan(rows))


def install(sample: str) -> str:
    """Register fixtures for one sample and return its (synthetic) address."""
    http.clear_fixtures()
    http.set_offline(True)
    addr = SAMPLES[sample]
    if sample == "complete":
        lat, lon, pin = 40.3801, -80.0491, "0000X00001000000"
        http.register_fixture("GET", _geocoder_url(addr),
                              {"candidates": [_cand("123 SAMPLE ST, PITTSBURGH, 15228", lat, lon, 100, pin, muni="MT LEBANON")]})
        http.register_fixture("GET", _assess_url(pin), _ckan([{
            "PARID": pin, "PROPERTYHOUSENUM": "123", "PROPERTYADDRESS": "SAMPLE ST", "PROPERTYZIP": "15228",
            "MUNIDESC": "Mt. Lebanon", "NEIGHCODE": "SYN01", "SCHOOLDESC": "Mt Lebanon", "USEDESC": "SINGLE FAMILY", "YEARBLT": "1928",
            "STYLE": "4", "STYLEDESC": "COLONIAL", "STORIES": "2", "BASEMENT": "5", "BASEMENTDESC": "Full",
            "EXTERIORFINISH": "2", "EXTFINISH_DESC": "Brick", "ROOF": "1", "ROOFDESC": "SHINGLE",
            "HEATINGCOOLING": "4", "HEATINGCOOLINGDESC": "Central Heat with AC", "CONDITION": "3", "CONDITIONDESC": "AVERAGE",
            "GRADE": "C+", "GRADEDESC": "AVERAGE +", "FIREPLACES": "1", "BSMTGARAGE": "1", "FINISHEDLIVINGAREA": "1850",
            "LOTAREA": "6200", "BEDROOMS": "3", "FULLBATHS": "1", "SALEDATE": "2026-09-15", "ASOFDATE": "2026-10-01"}]))
        _common_overlays(lat, lon, undermined=True, landslide=False)
        # SYNTHETIC comparable sales: invented prices, dated relative to today so the window logic is exercised.
        _comps("neighborhood", "SYN01", "SINGLE FAMILY", 1850, [
            (1, 1700, 168, 1931), (3, 2050, 175, 1925), (5, 1600, 182, 1940), (7, 1900, 186, 1928),
            (10, 2200, 190, 1935), (13, 1750, 195, 1922), (16, 1500, 201, 1948), (20, 2000, 212, 1930),
            (30, 1800, 150, 1926),   # outside the 24-month window
        ], bad_price=True)
    elif sample == "missing":
        lat, lon, pin = 40.4109, -79.9790, "0000X00002000000"
        http.register_fixture("GET", _geocoder_url(addr),
                              {"candidates": [_cand("456 PLACEHOLDER AVE, PITTSBURGH, 15210", lat, lon, 97, pin, muni="PITTSBURGH")]})
        http.register_fixture("GET", _assess_url(pin), _ckan([{
            "PARID": pin, "PROPERTYHOUSENUM": "456", "PROPERTYADDRESS": "PLACEHOLDER AVE", "PROPERTYZIP": "15210",
            "MUNIDESC": "18th Ward - PITTSBURGH", "NEIGHCODE": "SYN02", "SCHOOLDESC": "Pittsburgh", "USEDESC": "SINGLE FAMILY", "YEARBLT": "0",
            "STYLE": "", "STYLEDESC": "", "STORIES": "2", "BASEMENT": "", "BASEMENTDESC": "",
            "EXTERIORFINISH": "", "EXTFINISH_DESC": "Frame", "ROOF": "", "ROOFDESC": "",
            "HEATINGCOOLING": "", "HEATINGCOOLINGDESC": "", "CONDITION": "4", "CONDITIONDESC": "FAIR",
            "GRADE": "D", "GRADEDESC": "BELOW AVERAGE", "FIREPLACES": "0", "BSMTGARAGE": "0", "FINISHEDLIVINGAREA": "1120",
            "LOTAREA": "2900", "BEDROOMS": "2", "FULLBATHS": "1", "SALEDATE": "", "ASOFDATE": "2026-10-01"}]))
        http.register_fixture("GET", _permits_url(pin), _ckan([{
            "permit_id": "SYN-2022-0001", "permit_type": "Building", "work_type": "Roof", "owner_name": "REDACTED",
            "work_description": "REPLACE ASPHALT SHINGLE ROOF", "issue_date": "2022-06-14", "status": "Finaled",
            "total_project_value": "9500", "commercial_or_residential": "Residential"}]))
        # No flood fixture on purpose: demonstrates an overlay that could not be retrieved.
        _common_overlays(lat, lon, undermined=True, landslide=True, flood=False)
        # Too few SYNTHETIC comparable sales: the price assessment must come back unavailable.
        _comps("neighborhood", "SYN02", "SINGLE FAMILY", 1120, [(4, 1100, 96, 0), (9, 1250, 110, 0)])
        _comps("municipality", "18th Ward - PITTSBURGH", "SINGLE FAMILY", 1120, [(4, 1100, 96, 0), (9, 1250, 110, 0), (14, 980, 104, 0)])
    elif sample == "ambiguous":
        http.register_fixture("GET", _geocoder_url(addr), {"candidates": [
            _cand("100 MAIN ST, PITTSBURGH, 15201", 40.4700, -79.9600, 100, "0000X00003000000", muni="PITTSBURGH"),
            _cand("100 MAIN ST, CARNEGIE, 15106", 40.4080, -80.0830, 100, "0000X00004000000", muni="CARNEGIE")]})
    return addr
