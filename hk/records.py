"""Public records -> profile Fields.

WPRDC Property Assessments (CC0): building characteristics keyed by PARID.
City of Pittsburgh PLI Permits (CC-BY): permit history, City parcels only.

Every Field produced here is evidence_type=public_record, verification_status=unverified,
with the exact dataset field named in source_ref and the assessor caveats in limitations.
"""
from __future__ import annotations

import json
import re

from . import DATA, http
from .evidence import Field

WPRDC_API = "https://data.wprdc.org/api/action/datastore_search"
ASSESSMENTS_RESOURCE = "65855e14-549e-4992-b5be-d629afc676fa"
PERMITS_RESOURCE = "f4d1177a-f597-4c32-8cbf-7885f56253f6"

_CODES = json.loads((DATA / "codes" / "assessment_codes.json").read_text(encoding="utf-8"))

ASSESSOR_CAVEAT = ("Assessor record: a monthly snapshot of Allegheny County OPA data; characteristics "
                   "are recorded for valuation, interior access is not routine, and the record says "
                   "nothing about current equipment age or condition.")


def _records(resource: str, filters: dict, limit: int = 5) -> http.FetchResult:
    url = http.q(WPRDC_API, {"resource_id": resource, "filters": json.dumps(filters), "limit": str(limit)})
    return http.fetch(url)


def assessment_by_parid(parid: str) -> tuple[dict | None, http.FetchResult]:
    r = _records(ASSESSMENTS_RESOURCE, {"PARID": parid}, limit=2)
    if r.ok and isinstance(r.data, dict) and r.data.get("success"):
        recs = r.data.get("result", {}).get("records", [])
        if recs:
            return recs[0], r
    return None, r


def _int(v):
    try:
        i = int(float(v))
        return i if i > 0 else None
    except (TypeError, ValueError):
        return None


def _desc(rec: dict, code_col: str, desc_col: str, table: str | None = None):
    d = (rec.get(desc_col) or "").strip()
    if d:
        return d
    c = str(rec.get(code_col) or "").strip()
    if table and c in _CODES.get(table, {}):
        return _CODES[table][c]
    return None


def fields_from_assessment(rec: dict, retrieved: str | None, source_ref_prefix: str) -> list[Field]:
    """Translate an assessor record into source-tagged Fields. Missing values become unknown Fields."""
    parid = rec.get("PARID", "")
    ref = lambda col: f"{source_ref_prefix} PARID {parid}, column {col}"
    asof = rec.get("ASOFDATE") or rec.get("RECORDDATE")
    out: list[Field] = []

    def pub(name, value, col, units=None, limitations=ASSESSOR_CAVEAT, note=""):
        out.append(Field(name=name, value=value, units=units, source_id="wprdc_assessments",
                         source_ref=ref(col), observed_date=asof, retrieved_date=retrieved,
                         evidence_type="public_record" if value is not None else "unknown",
                         verification_status="unverified" if value is not None else "unknown",
                         limitations=limitations,
                         note=note if value is not None else ("blank in assessor record" + (f"; {note}" if note else ""))))

    pub("parcel_id", parid or None, "PARID", limitations="")
    pub("municipality", (rec.get("MUNIDESC") or "").strip() or None, "MUNIDESC", limitations="")
    pub("neighborhood_code", (str(rec.get("NEIGHCODE") or "")).strip() or None, "NEIGHCODE",
        limitations="Assessor's valuation neighbourhood; used to find comparable sales.")
    pub("school_district", (rec.get("SCHOOLDESC") or "").strip() or None, "SCHOOLDESC", limitations="")
    pub("use_description", (rec.get("USEDESC") or "").strip() or None, "USEDESC", limitations="")
    yb = _int(rec.get("YEARBLT"))
    pub("year_built", yb, "YEARBLT",
        note="How YEARBLT is derived is not documented by OPA; treat as construction era, not a precise date.")
    pub("style", _desc(rec, "STYLE", "STYLEDESC"), "STYLEDESC")
    pub("stories", (lambda v: float(v) if v not in (None, "") else None)(rec.get("STORIES")), "STORIES")
    pub("basement", _desc(rec, "BASEMENT", "BASEMENTDESC", "BASEMENT"), "BASEMENTDESC",
        note="Assessor basement category (None/Slab-Piers/Crawl/Part/Full); does not describe finish or water history.")
    pub("exterior_finish", _desc(rec, "EXTERIORFINISH", "EXTFINISH_DESC"), "EXTFINISH_DESC")
    pub("roof_type", _desc(rec, "ROOF", "ROOFDESC"), "ROOFDESC",
        note="Roof covering type as recorded by the assessor; not its age or condition.")
    pub("heating_cooling", _desc(rec, "HEATINGCOOLING", "HEATINGCOOLINGDESC"), "HEATINGCOOLINGDESC",
        note="Heating/cooling category only (e.g. 'Central Heat with AC'); fuel and equipment age are not recorded.")
    pub("condition_assessor", _desc(rec, "CONDITION", "CONDITIONDESC", "CONDITION"), "CONDITIONDESC",
        note="Assessor valuation category — not an inspection finding.")
    pub("grade_assessor", _desc(rec, "GRADE", "GRADEDESC"), "GRADEDESC",
        note="Quality-of-construction grade used for valuation.")
    pub("fireplaces", _int(rec.get("FIREPLACES")) or (0 if rec.get("FIREPLACES") not in (None, "") else None),
        "FIREPLACES")
    pub("basement_garage_cars", _int(rec.get("BSMTGARAGE")) or (0 if rec.get("BSMTGARAGE") not in (None, "") else None),
        "BSMTGARAGE")
    pub("living_area", _int(rec.get("FINISHEDLIVINGAREA")), "FINISHEDLIVINGAREA", units="sq ft",
        note="Estimated from exterior measurement per OPA user guide.")
    pub("lot_area", _int(rec.get("LOTAREA")), "LOTAREA", units="sq ft")
    pub("bedrooms", _int(rec.get("BEDROOMS")), "BEDROOMS")
    pub("full_baths", _int(rec.get("FULLBATHS")), "FULLBATHS")
    pub("last_sale_date", (rec.get("SALEDATE") or None), "SALEDATE", limitations="Recording lag of weeks; validity code may change.")
    return out


def is_city_of_pittsburgh(munidesc: str | None) -> bool:
    return bool(munidesc) and bool(re.search(r"PITTSBURGH", munidesc, re.I)) and "Ward" in munidesc or \
        bool(munidesc) and munidesc.strip().upper() == "PITTSBURGH"


def permits_by_parcel(parid: str) -> tuple[list[dict], http.FetchResult]:
    """City of Pittsburgh PLI permits. Owner names are present in the dataset and are dropped here."""
    r = _records(PERMITS_RESOURCE, {"parcel_num": parid}, limit=50)
    out: list[dict] = []
    if r.ok and isinstance(r.data, dict) and r.data.get("success"):
        for p in r.data.get("result", {}).get("records", []):
            out.append({k: p.get(k) for k in ("permit_id", "permit_type", "work_type", "work_description",
                                               "issue_date", "status", "total_project_value",
                                               "commercial_or_residential")})
    return out, r


# ---------------------------------------------------------------- comparable sales (price benchmark)
WPRDC_SQL = "https://data.wprdc.org/api/action/datastore_search_sql"
COMP_COLUMNS = ("PARID", "SALEPRICE", "SALEDATE", "SALEDESC", "FINISHEDLIVINGAREA", "YEARBLT", "USEDESC", "NEIGHCODE", "MUNIDESC")
BENCHMARK_LIMITS = ("Built from each similar parcel's most recent recorded sale in the county assessment file (the county's "
                    "'valid sale' classification marks arm's-length sales). Prices are not adjusted for condition, updates, "
                    "lot, or market change since the sale; living area is the assessor's exterior-measured estimate. "
                    "Tax assessments are not used. Not an appraisal.")


def _sql_str(v: str) -> str:
    return "'" + str(v).replace("'", "''") + "'"


def comps_sql(scope: str, value: str, use: str, lo: int, hi: int) -> str:
    col = {"neighborhood": "NEIGHCODE", "municipality": "MUNIDESC"}[scope]
    cols = ",".join('"%s"' % c for c in COMP_COLUMNS)
    return (f'SELECT {cols} FROM "{ASSESSMENTS_RESOURCE}" WHERE "{col}" = {_sql_str(value)} '
            f'AND "USEDESC" = {_sql_str(use)} AND "SALEDESC" ILIKE {_sql_str("VALID%")} '
            f'AND "SALEPRICE" > 0 AND "FINISHEDLIVINGAREA" BETWEEN {int(lo)} AND {int(hi)} LIMIT 2000')


def comps_url(scope: str, value: str, use: str, lo: int, hi: int) -> str:
    return http.q(WPRDC_SQL, {"sql": comps_sql(scope, value, use, lo, hi)})


def size_band(area: int, tol: float) -> tuple[int, int]:
    return int(round(area * (1 - tol))), int(round(area * (1 + tol)))


def parse_sale_date(s):
    """County assessment SALEDATE is text, observed as MM-DD-YYYY; ISO dates are accepted too."""
    import datetime as _dt
    if not s:
        return None
    s = str(s).strip()[:10]
    for fmt in ("%m-%d-%Y", "%Y-%m-%d", "%m/%d/%Y"):
        try:
            return _dt.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def price_benchmark(p, cfg: dict) -> Field:
    """Median price per finished sq ft of recent valid sales of similar homes nearby.

    Tiers: same assessor neighbourhood, then same municipality; same use description; living area
    within +/- size_tolerance; sold within window_months (extended once if too few). The era filter
    (year built +/- era_tolerance_years) is applied only when enough sales survive it.
    """
    import datetime as _dt
    import statistics
    name = "price_benchmark"
    area, use = p.value("living_area"), p.value("use_description")
    muni, neigh, parid = p.value("municipality"), p.value("neighborhood_code"), p.value("parcel_id")
    yb = p.value("year_built")
    if not area or not use or not (muni or neigh):
        missing = [n for n, v in (("living area", area), ("property type", use), ("municipality", muni or neigh)) if not v]
        return Field(name=name, value=None, note="no benchmark: " + ", ".join(missing) + " not recorded")
    lo, hi = size_band(int(area), cfg["size_tolerance"])
    today = _dt.date.today()
    tried = []
    for scope, val in (("neighborhood", neigh), ("municipality", muni)):
        if not val:
            continue
        r = http.fetch(comps_url(scope, val, use, lo, hi), max_age_days=30)
        if not (r.ok and isinstance(r.data, dict) and r.data.get("success")):
            tried.append(f"{scope}: lookup failed ({r.reason or 'no data'})")
            continue
        rows = []
        for rec in r.data.get("result", {}).get("records", []):
            d = parse_sale_date(rec.get("SALEDATE"))
            try:
                price, sq = float(rec.get("SALEPRICE") or 0), float(rec.get("FINISHEDLIVINGAREA") or 0)
            except (TypeError, ValueError):
                continue
            if not d or d > today or price < cfg["min_sale_price"] or sq <= 0 or rec.get("PARID") == parid:
                continue
            rows.append({"date": d, "price": price, "sqft": sq, "ppsf": price / sq, "year": _int(rec.get("YEARBLT"))})
        for months in (cfg["window_months"], cfg["extended_window_months"]):
            cutoff = today - _dt.timedelta(days=int(months * 30.44))
            recent = [x for x in rows if x["date"] >= cutoff]
            era = [x for x in recent if yb and x["year"] and abs(x["year"] - int(yb)) <= cfg["era_tolerance_years"]]
            use_rows, era_used = (era, True) if yb and len(era) >= cfg["min_comparables"] else (recent, False)
            if len(use_rows) >= cfg["min_comparables"]:
                pp = sorted(x["ppsf"] for x in use_rows)
                q = statistics.quantiles(pp, n=4) if len(pp) >= 4 else [pp[0], statistics.median(pp), pp[-1]]
                val = {"median_ppsf": round(statistics.median(pp)), "q1_ppsf": round(q[0]), "q3_ppsf": round(q[2]),
                       "n": len(pp), "scope": scope, "scope_value": val, "use": use, "size_band": [lo, hi],
                       "window_months": months, "era_filter": era_used,
                       "oldest_sale": min(x["date"] for x in use_rows).isoformat(),
                       "newest_sale": max(x["date"] for x in use_rows).isoformat(),
                       "sales": [{"date": x["date"].isoformat(), "price": round(x["price"]), "sqft": int(x["sqft"]),
                                  "ppsf": round(x["ppsf"])} for x in sorted(use_rows, key=lambda x: x["date"], reverse=True)]}
                return Field(name=name, value=val, source_id="wprdc_assessments",
                             source_ref=f"WPRDC datastore_search_sql on assessments: {scope} = {val['scope_value']}, USEDESC = {use}, "
                                        f"SALEDESC like VALID, living area {lo}-{hi} sq ft",
                             retrieved_date=r.retrieved, evidence_type="public_record", verification_status="unverified",
                             limitations=BENCHMARK_LIMITS)
            tried_n = len(use_rows)
        tried.append(f"{scope}: {tried_n} similar valid sales in {cfg['extended_window_months']} months")
    return Field(name=name, value=None, note="too few comparable sales — " + "; ".join(tried) if tried else "no comparable-sales lookup possible",
                 limitations=BENCHMARK_LIMITS)
