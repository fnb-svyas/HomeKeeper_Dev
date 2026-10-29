"""Regional-exposure overlays. Each returns a Field with evidence_type=regional_exposure
and a `limitations` string that states what the overlay does NOT establish.

A failed lookup returns an unknown Field whose note says why, so the gap is visible.
"""
from __future__ import annotations

import json
import statistics

from . import http
from .evidence import Field

RADON = "https://data.pa.gov/resource/vkjb-sx3k.json"
NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer"
MSI = ("https://gis.dep.pa.gov/depgisprd/rest/services/MineSubsidenceInsurance/"
       "MSI_SubsidenceRiskMiningConfirmed/MapServer/0/query")
PASDA_AC = "https://mapservices.pasda.psu.edu/server/rest/services/pasda/AlleghenyCounty/MapServer"
LANDSLIDE_LAYER = 37
SDA = "https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest"
NCEI = "https://www.ncei.noaa.gov/access/services/data/v1"
NCEI_STATION = "USW00094823"  # Pittsburgh International Airport


def _fail(name: str, r: http.FetchResult, what: str) -> Field:
    return Field(name=name, value=None, note=f"{what} not retrieved: {r.reason or 'no data'}",
                 source_ref=r.url)


# ---------------------------------------------------------------- radon (PA DEP)
def radon_zip_stats(zip_code: str) -> Field:
    """Basement-floor test statistics for a ZIP from PA DEP data (public domain)."""
    url = http.q(RADON, {"$select": "measure_value,test_end_date,test_floor_level_text,mitigation_system_indicator",
                         "$where": f"address_postal_code='{zip_code}' AND county_name='Allegheny'",
                         "$limit": "50000"})
    r = http.fetch(url, max_age_days=90)
    if not r.ok or not isinstance(r.data, list):
        return _fail("radon_zip_stats", r, "PA DEP radon test history")
    vals = []
    basement = 0
    for row in r.data:
        try:
            v = float(row.get("measure_value"))
        except (TypeError, ValueError):
            continue
        vals.append(v)
        if "BASEMENT" in (row.get("test_floor_level_text") or "").upper():
            basement += 1
    if not vals:
        return Field(name="radon_zip_stats", value=None, note=f"no DEP tests on file for ZIP {zip_code}")
    vals.sort()
    stats = {"zip": zip_code, "tests": len(vals), "basement_tests": basement,
             "median_pci_l": round(statistics.median(vals), 1),
             "pct_at_or_above_4": round(100.0 * sum(v >= 4.0 for v in vals) / len(vals)),
             "latest_test": max((row.get("test_end_date") or "")[:10] for row in r.data)}
    return Field(name="radon_zip_stats", value=stats, units="pCi/L", source_id="padep_radon_tests",
                 source_ref=f"data.pa.gov vkjb-sx3k, address_postal_code={zip_code}, county_name=Allegheny",
                 observed_date=stats["latest_test"] or None, retrieved_date=r.retrieved,
                 evidence_type="regional_exposure", verification_status="unverified",
                 limitations=("Self-selected tests reported by certified testers; includes post-mitigation tests; "
                              "ZIP is not a municipality. Describes neighbours' results, not this house. "
                              "Only a test in this house establishes its radon level."))


# ---------------------------------------------------------------- flood (FEMA NFHL)
def flood_zone(lat: float, lon: float) -> Field:
    url = http.q(f"{NFHL}/28/query", {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint",
                                        "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
                                        "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE",
                                        "returnGeometry": "false", "f": "json"})
    r = http.fetch(url, max_age_days=180)
    if not r.ok or not isinstance(r.data, dict) or "features" not in r.data:
        return _fail("flood_zone", r, "FEMA flood zone")
    feats = r.data.get("features", [])
    if not feats:
        val = {"fld_zone": None, "sfha": None, "note": "no NFHL polygon at this point (unmapped or outside coverage)"}
    else:
        a = feats[0].get("attributes", {})
        val = {"fld_zone": a.get("FLD_ZONE"), "zone_subtype": a.get("ZONE_SUBTY"),
               "sfha": (a.get("SFHA_TF") == "T"), "static_bfe": a.get("STATIC_BFE")}
    return Field(name="flood_zone", value=val, source_id="fema_nfhl",
                 source_ref="NFHL MapServer layer 28 (S_Fld_Haz_Ar) point intersect; LOMA layer 2 not checked",
                 retrieved_date=r.retrieved, evidence_type="regional_exposure", verification_status="unverified",
                 limitations=("Mapped zone containment at FIRM-panel scale; a LOMA may remove the structure; Zone X "
                              "still has basement-flooding exposure. Does not establish whether this basement takes water."))


# ---------------------------------------------------------------- mine subsidence (PA DEP)
def undermined(lat: float, lon: float) -> Field:
    url = http.q(MSI, {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326",
                       "spatialRel": "esriSpatialRelIntersects", "outFields": "ID", "returnGeometry": "false",
                       "f": "json"})
    r = http.fetch(url, max_age_days=180)
    if not r.ok or not isinstance(r.data, dict) or "features" not in r.data:
        return _fail("undermined", r, "DEP mine-subsidence risk layer")
    flag = bool(r.data.get("features"))
    return Field(name="undermined", value=flag, source_id="padep_msi_layer",
                 source_ref="DEP MSI_SubsidenceRiskMiningConfirmed layer 0 point intersect",
                 retrieved_date=r.retrieved, evidence_type="regional_exposure", verification_status="unverified",
                 limitations=("DEP layer of areas known to be undermined or near undermined areas, from mine maps of "
                              "varying accuracy. Not a parcel-level mine map review and not evidence of movement. "
                              "License: not for commercial use or resale — flag and link only."))


# ---------------------------------------------------------------- landslide (Allegheny County via PASDA)
def landslide_prone(lat: float, lon: float) -> Field:
    url = http.q(f"{PASDA_AC}/{LANDSLIDE_LAYER}/query",
                 {"geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": "4326",
                  "spatialRel": "esriSpatialRelIntersects", "outFields": "landslidep", "returnGeometry": "false",
                  "f": "json"})
    r = http.fetch(url, max_age_days=180)
    if not r.ok or not isinstance(r.data, dict) or "features" not in r.data:
        return _fail("landslide_prone", r, "Allegheny County landslide-prone layer")
    flag = bool(r.data.get("features"))
    return Field(name="landslide_prone", value=flag, source_id="pasda_landslide_prone",
                 source_ref=f"PASDA AlleghenyCounty MapServer layer {LANDSLIDE_LAYER} (Landslide Prone 202509) point intersect",
                 retrieved_date=r.retrieved, evidence_type="regional_exposure", verification_status="unverified",
                 limitations=("Coarse slope/geology zone; the published layer covers the City of Pittsburgh extent only, so "
                              "False outside the city means 'not mapped', not 'not prone'. Does not establish slope "
                              "movement at this lot."))


# ---------------------------------------------------------------- soils (NRCS SSURGO via SDA)
SDA_SQL = """SELECT TOP 1 mu.mukey, mu.muname, c.compname, c.comppct_r, c.drainagecl, c.hydricrating,
       c.frostact, c.corcon, c.corsteel, ma.wtdepannmin, ma.drclassdcd, ma.flodfreqdcd
FROM mapunit mu
JOIN component c ON c.mukey = mu.mukey AND c.majcompflag = 'Yes'
LEFT JOIN muaggatt ma ON ma.mukey = mu.mukey
WHERE mu.mukey IN (SELECT * FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('point({lon} {lat})'))
ORDER BY c.comppct_r DESC"""


def soil_map_unit(lat: float, lon: float) -> Field:
    r = http.fetch(SDA, method="POST", data={"query": SDA_SQL.format(lon=lon, lat=lat), "format": "JSON+COLUMNNAME"},
                   max_age_days=365)
    if not r.ok or not isinstance(r.data, dict) or not r.data.get("Table"):
        return _fail("soil_map_unit", r, "NRCS soil map unit")
    rows = r.data["Table"]
    if len(rows) < 2:
        return Field(name="soil_map_unit", value=None, note="no soil map unit at this point")
    cols, vals = rows[0], rows[1]
    rec = dict(zip(cols, vals))
    return Field(name="soil_map_unit", value=rec, source_id="nrcs_sda",
                 source_ref="SDA Tabular/post.rest: mapunit/component/muaggatt for mukey at WGS84 point",
                 retrieved_date=r.retrieved, evidence_type="regional_exposure", verification_status="unverified",
                 limitations=("SSURGO map unit (1:12,000–1:63,360) describing the dominant soil of a polygon that may "
                              "cover many lots; urban map units carry few attributes. Not a foundation condition; "
                              "NRCS says it does not replace on-site investigation."))


# ---------------------------------------------------------------- climate normals (NCEI)
def climate_normals() -> Field:
    url = http.q(NCEI, {"dataset": "normals-annualseasonal", "stations": NCEI_STATION, "format": "json",
                        "dataTypes": ("ANN-HTDD-NORMAL,ANN-PRCP-NORMAL,ANN-SNOW-NORMAL,"
                                      "ANN-TMIN-PRBFST-T32FP50,ANN-TMIN-PRBLST-T32FP50")})
    r = http.fetch(url, max_age_days=365)
    if not r.ok or not isinstance(r.data, list) or not r.data:
        return _fail("climate_normals", r, "NCEI climate normals")
    d = r.data[0]
    def num(k, scale):
        try:
            return round(float(d[k]) / scale, 1)
        except (KeyError, TypeError, ValueError):
            return None
    val = {"station": d.get("STATION"), "first_freeze_median": d.get("ANN-TMIN-PRBFST-T32FP50"),
           "last_freeze_median": d.get("ANN-TMIN-PRBLST-T32FP50"),
           "heating_degree_days_base65": num("ANN-HTDD-NORMAL", 1),
           "annual_precip_in": num("ANN-PRCP-NORMAL", 100), "annual_snow_in": num("ANN-SNOW-NORMAL", 10)}
    return Field(name="climate_normals", value=val, source_id="ncei_normals",
                 source_ref=f"NCEI Access Data Service normals-annualseasonal 1991-2020, station {NCEI_STATION}",
                 observed_date="1991-2020", retrieved_date=r.retrieved, evidence_type="regional_exposure",
                 verification_status="unverified",
                 limitations=("30-year station normals at Pittsburgh International Airport; freeze dates are 50% "
                              "probabilities, not forecasts; no site microclimate."))
