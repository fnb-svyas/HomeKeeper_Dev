"""`python homekeeper.py doctor` — live checks of every endpoint the prototype depends on.

Run this on the machine that will run the app. It prints one line per endpoint with the
HTTP status, the response shape, and the first field names, and writes
audit/doctor_results.json so the result can be filed with the audit.
"""
from __future__ import annotations

import json
import time

from . import ROOT, http, geocode, records, overlays

TEST_ADDRESS = "710 Washington Rd, Pittsburgh, PA 15228"   # Mt. Lebanon municipal building (public address)
TEST_LAT, TEST_LON = 40.3794, -80.0453

CHECKS = [
    ("county_geocoder", lambda: http.fetch(http.q(geocode.COUNTY_GEOCODER,
        {"SingleLine": TEST_ADDRESS, "outSR": "4326", "maxLocations": "3", "outFields": "*", "f": "json"}), max_age_days=0)),
    ("county_parcel_features", lambda: http.fetch(http.q(geocode.COUNTY_PARCELS,
        {"geometry": f"{TEST_LON},{TEST_LAT}", "geometryType": "esriGeometryPoint", "inSR": "4326",
         "spatialRel": "esriSpatialRelWithin", "outFields": "PIN,MUNICODE", "returnGeometry": "false", "f": "json"}), max_age_days=0)),
    ("wprdc_assessments", lambda: http.fetch(http.q(records.WPRDC_API,
        {"resource_id": records.ASSESSMENTS_RESOURCE, "limit": "1"}), max_age_days=0)),
    ("wprdc_comparable_sales", lambda: http.fetch(records.comps_url("municipality", "Mt. Lebanon", "SINGLE FAMILY", 1300, 2400), max_age_days=0)),
    ("pgh_pli_permits", lambda: http.fetch(http.q(records.WPRDC_API,
        {"resource_id": records.PERMITS_RESOURCE, "limit": "1"}), max_age_days=0)),
    ("padep_radon_tests", lambda: http.fetch(http.q(overlays.RADON,
        {"$select": "count(*)", "county_name": "Allegheny"}), max_age_days=0)),
    ("fema_nfhl", lambda: http.fetch(http.q(f"{overlays.NFHL}/28/query",
        {"geometry": f"{TEST_LON},{TEST_LAT}", "geometryType": "esriGeometryPoint", "inSR": "4326",
         "spatialRel": "esriSpatialRelIntersects", "outFields": "FLD_ZONE,SFHA_TF", "returnGeometry": "false", "f": "json"}), max_age_days=0)),
    ("padep_msi_layer", lambda: http.fetch(http.q(overlays.MSI,
        {"geometry": f"{TEST_LON},{TEST_LAT}", "geometryType": "esriGeometryPoint", "inSR": "4326",
         "outFields": "ID", "returnGeometry": "false", "f": "json"}), max_age_days=0)),
    ("pasda_landslide_prone", lambda: http.fetch(http.q(f"{overlays.PASDA_AC}/{overlays.LANDSLIDE_LAYER}/query",
        {"where": "1=1", "returnCountOnly": "true", "f": "json"}), max_age_days=0)),
    ("nrcs_sda", lambda: http.fetch(overlays.SDA, method="POST",
        data={"query": overlays.SDA_SQL.format(lon=TEST_LON, lat=TEST_LAT), "format": "JSON+COLUMNNAME"}, max_age_days=0)),
    ("ncei_normals", lambda: http.fetch(http.q(overlays.NCEI,
        {"dataset": "normals-annualseasonal", "stations": overlays.NCEI_STATION, "format": "json",
         "dataTypes": "ANN-TMIN-PRBFST-T32FP50"}), max_age_days=0)),
    ("census_geocoder", lambda: http.fetch(http.q(geocode.CENSUS,
        {"address": TEST_ADDRESS, "benchmark": "Public_AR_Current", "format": "json"}), max_age_days=0)),
    ("nws_api_points", lambda: http.fetch(f"https://api.weather.gov/points/{TEST_LAT},{TEST_LON}", max_age_days=0)),
]


def _shape(data) -> str:
    if isinstance(data, dict):
        keys = list(data.keys())[:6]
        inner = ""
        for k in ("candidates", "features", "result", "Table"):
            if k in data:
                v = data[k]
                if isinstance(v, dict):
                    v = v.get("records", v)
                inner = f"; {k}: {len(v) if hasattr(v, '__len__') else type(v).__name__}"
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    inner += f" first keys {list(v[0].keys())[:8]}"
                break
        return f"dict keys {keys}{inner}"
    if isinstance(data, list):
        first = data[0] if data else None
        return f"list[{len(data)}]" + (f" first keys {list(first.keys())[:8]}" if isinstance(first, dict) else "")
    return f"{type(data).__name__} ({str(data)[:80]!r})"


def run(verbose: bool = True) -> dict:
    results = {"ran": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "address": TEST_ADDRESS, "checks": {}}
    for name, fn in CHECKS:
        t0 = time.time()
        r = fn()
        dt = round(time.time() - t0, 2)
        entry = {"ok": r.ok, "status": r.status, "seconds": dt, "reason": r.reason,
                 "shape": _shape(r.data) if r.ok else None, "url": r.url}
        results["checks"][name] = entry
        if verbose:
            mark = "OK " if r.ok else "FAIL"
            print(f"[{mark}] {name:<24} {r.status or '-':>4}  {dt:5.2f}s  {entry['shape'] or r.reason}")
    out = ROOT / "audit" / "doctor_results.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    if verbose:
        ok = sum(1 for c in results["checks"].values() if c["ok"])
        print(f"\n{ok}/{len(CHECKS)} endpoints reachable. Results written to {out}")
    return results
