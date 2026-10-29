# HomeKeeper — Checkpoint 1: Data-Supply Audit

Audited 2026-10-29. Pilot: Allegheny County, PA; existing single-family homes with basements built before 1960; buyers under contract with an inspection report, through the first 90 days of ownership. Constraint: Windows + Python standard library, no required paid API keys.

Detail per source is in `audit/tracks/01–04*.md`; the machine-readable registry is `data/sources.json` (64 entries). This file is the decision summary.

Verification legend: **live** = a real request was made and the response shape confirmed during the audit; **doc** = access method and terms read from the publisher's own documentation, not yet called; **unverified** = could not be confirmed, stated as such.

## 1. Feasibility decision

**Go.** The pilot can be built at zero software cost from free, keyless sources, and the three facts that matter most for a pre-1960 Allegheny house are all available:

1. **Parcel-level building characteristics** (year built, basement type, stories, exterior, roof type, heating type, assessor condition/grade) come from the WPRDC assessments dataset under **CC0**, keyed by a parcel ID that the county's own geocoder returns from a single GET (live).
2. **Hazard overlays that change a recommendation** — PA DEP radon test history by ZIP (live, public domain), DEP confirmed-mining layer (live), county landslide-prone layer (live), FEMA flood zone (doc), NRCS soil map unit (doc) — are all point-queryable without a key.
3. **The rule base can be sourced** from public-domain federal guidance (DOE, EPA, CPSC/USFA) for the recurring safety and maintenance items, with manufacturer manuals linked (not mirrored) for equipment-specific intervals, and a small set of attributed private sources (InterNACHI, CSIA, NRCA via Professional Roofing, ISU Extension) for scope, age ranges and drainage figures.

Three findings change the plan from what was assumed in the pilot proposal:

- **The county geocoder replaces the address-points download as the primary address→parcel path.** `AddressVerification/findAddressCandidates` returns PARCELID and WGS84 coordinates in one call. The address-point file (~474k points) stays as an offline fallback.
- **Provider "licensing" is narrower than hoped.** PA has no state license for general contractors, electricians or HVAC. Verifiable credentials are limited to: ACHD registered master plumbers (CC0 CSV, frozen since July 2026), City of Pittsburgh trade licenses (CC0, weekly, city only), PA DEP radon certification (monthly PDFs), and HICPA registration (restored April 2026; manual lookup only). The provider layer will be a small, hand-checked directory with literal dated evidence wording, as the brief allows.
- **Two useful PA layers are non-commercial.** The DEP mine-subsidence and mined-out layers say "Not for commercial use or resale." The prototype will show a derived yes/no flag and a link to DEP's own map; this needs legal review before any commercial use.

**No free, licensable local cost source exists.** Cost sites (Angi/HomeAdvisor, Fixr, Cost vs. Value) prohibit reproduction. Budgets will run on user-entered quotes and explicitly labeled planning assumptions, as the brief requires. County AHILP loan caps and URA program caps are "financing exists" facts, not prices.

## 2. What will be integrated (Checkpoint 2–4)

| # | Source | Access | Point query | License | Verification | Product use |
|---|---|---|---|---|---|---|
| 1 | County AddressVerification geocoder | ArcGIS REST GET | address → PARCELID + lat/lon | county disclaimer (non-commercial) | live | parcel match, ambiguity handling |
| 2 | WPRDC Property Assessments | CKAN datastore API / bulk CSV | PARID | CC0 | doc | house profile fields |
| 3 | County Parcel_Features point-in-polygon | ArcGIS REST GET | lat/lon → PIN | county disclaimer | live | fallback parcel match |
| 4 | WPRDC Address Points (PASDA GeoJSON) | download once | address → PARCELID | unspecified (as-is) | doc | offline fallback |
| 5 | City of Pittsburgh PLI Permits | CKAN / CSV | parcel_num | CC-BY | doc | recent permit history (City homes only) |
| 6 | PA DEP radon tests (data.pa.gov vkjb-sx3k) | SODA GET | ZIP / municipality | Public Domain | live | ZIP radon history card; test/mitigate task |
| 7 | FEMA NFHL layer 28 (+ LOMA layer 2) | ArcGIS REST GET | lat/lon | US Gov + non-endorsement | doc | flood zone card; basement/sump tasks |
| 8 | DEP MSI confirmed-mining layer | ArcGIS REST GET | lat/lon | non-commercial | live | undermined flag + MSI task (link out) |
| 9 | PASDA Landslide Prone (City) + SPC past landslides | ArcGIS REST GET / GeoJSON | lat/lon | county as-is | live | hillside flag → drainage/retaining-wall tasks |
| 10 | NRCS SSURGO via Soil Data Access | POST SQL | WKT point → mukey | public | doc | soil/foundation context (drainage class, water table, frost action) |
| 11 | NCEI Climate Normals (USW00094823) | GET JSON | station | public domain | live | seasonal windows (first freeze ~Oct 20, last ~Apr 24) |
| 12 | Municipal dye-test rules (9 municipalities) | hand-curated table | municipality | public law | doc | before-you-buy deadline item |
| 13 | PA Seller Disclosure Law + form | web/PDF | n/a | public law | doc | "ask the disclosure for…" prompts |
| 14 | DOE Energy Saver, EPA radon/mold/lead guides, CPSC/USFA alarm/CO/dryer/GFCI pubs | web/PDF | n/a | public domain / non-commercial free | doc | core rule citations |
| 15 | InterNACHI SOP + life-expectancy chart; NAHB 2007 (mirror) | web | n/a | copyright → link + attributed paraphrase | doc | scope explainer; age-based planning windows |
| 16 | CSIA, NRCA (via Professional Roofing), ISU Extension Pm-1560, Penn State Extension | web | n/a | copyright → attributed paraphrase | doc | chimney, roof, grading rules |
| 17 | Manufacturer manuals/warranties: Zoeller, Liberty, Carrier, Goodman, Bradford White, A. O. Smith | PDF (link only) | n/a | copyright; no mirroring | doc | equipment-specific intervals and warranty-registration tasks |
| 18 | ACHD master plumbers (WPRDC CSV) | CSV | n/a | CC0 | doc | plumber licensing evidence (frozen list, dated) |
| 19 | City of Pittsburgh trade/contractor licenses (WPRDC) | CSV | n/a | CC0 | doc | electrician licensing evidence (City only) |
| 20 | PA DEP certified radon lists | monthly PDF | county | public | doc | radon provider evidence (manual extract) |
| 21 | PA AG HICPA search | web UI / phone | manual | public record | doc | registration evidence, recorded manually with date |
| 22 | Census Geocoder | GET JSON | address | public | live | fallback geocoder |

## 3. What is deferred, and why

| Source | Decision | Reason |
|---|---|---|
| NWS api.weather.gov | defer to Checkpoint 7 | works keyless (User-Agent required) but weather automation distracts from core pilot; county UGC PAC003 / zone PAZ021 recorded |
| WPRDC Sale Transactions | defer | user knows their closing date; weeks of lag; code list unpublished |
| ACHD Plumbing Inspections | defer | feed suspended July 2026, undercounting, no parcel ID |
| County Real Estate Portal | link only | daily-fresh but no API; county ToS bars commercial use/scraping |
| PWSA lead service line map | link-out task | ArcGIS Experience app only; feature service unpublished |
| EPA Radon Zones map | static sentence | DEP test data is better; Allegheny zone not yet read from primary PDF |
| Termite probability (IRC R301.2) | static sentence | "moderate to heavy" per Shaler Twp UCC ordinance; cite ordinance, never the ICC figure |
| USDA hardiness zone | hard-coded label | landscaping only |
| Wildfire | omit | not material in Allegheny County |
| Nominatim / Overpass (OSM) | defer | usage policy forbids primary geocoding use; provider counts unverified and existence-only |
| EPA 608 / NATE, CSIA locator, BBB, Google Places, Yelp, Angi/Thumbtack | defer or omit | no name lookup, scraping prohibited, or paid/key-required; none yields credential evidence the app may display |
| PASDA mined-out areas, Mine Map Atlas | link | incomplete historic permits; non-commercial |
| ACHD Article XV (ICC Digital Codes) | link | ICC platform; free tier unverified |
| NFPA 72/54/211, ASHRAE 169, IECC tables | not used | paid standards; CPSC/USFA/PNNL/PHRC state the same facts in free sources |

**First likely paid service:** Google Places API (New). It would buy business existence, hours and reviews near the address, but requires a billing-enabled key, forbids storing provider names/addresses, and gives weaker evidence than the public registries above — so it is unnecessary for the prototype.

## 4. Regional exposure vs. verified condition (how each overlay will be worded)

| Overlay | What it establishes | What it does not establish | The verified-condition source |
|---|---|---|---|
| DEP radon tests by ZIP | neighbors' reported results | this house's level | a test in this house (inspection 48-h test) |
| FEMA flood zone | mapped zone polygon containment | whether this basement takes water | inspection report; seller disclosure item 4; LOMA layer |
| SSURGO map unit | dominant soil of a polygon covering many lots | foundation condition | inspector's observations of cracks, efflorescence, grading |
| DEP confirmed mining | mining mapped under/near the point | parcel-level mine map or subsidence | coal status report; inspection; MSI application |
| Landslide-prone | coarse slope/geology zone | slope movement at this lot | retaining-wall/slope notes in inspection |
| Climate normals | 30-year probabilities | this week's weather | NWS forecast/alerts (Checkpoint 7) |
| Year built (assessor) | construction era | equipment age | labels, invoices, inspection report |

## 5. Licensing classes used in `sources.json`

- **redistribute** — CC0 / public domain; may be cached and shipped with the app (assessments, radon tests, NCEI, Census, DOE, CPSC, PA statutes).
- **attribute** — may be used/cached with attribution and disclaimer (CC-BY permits, FEMA, county GIS, NRCS, PASDA county layers).
- **paraphrase_attribute** — private copyright; short attributed paraphrase + link (InterNACHI, CSIA, NRCA, ISU/PSU Extension, municipal code text).
- **link_only** — restrictive terms or non-commercial license; the app stores a citation and a derived value at most (manufacturer manuals, BSC, DEP mining layers, HICPA search, county portal).
- **paid** — not used in the prototype (Google Places, Yelp, NFPA/ASHRAE/ICC).

## 6. Items to verify on the Windows machine in Checkpoint 2 (the research sandbox's proxy blocked them)

1. Live `datastore_search` call against WPRDC resource `65855e14-549e-4992-b5be-d629afc676fa` with `filters={"PARID": "..."}` — confirm response shape and whether PROPERTYADDRESS includes the street suffix.
2. FEMA NFHL layer 28 point query response for a test coordinate; confirm LOMA layer 2 query.
3. SSURGO `Tabular/post.rest` POST with `SDA_Get_Mukey_from_intersection_with_WktWgs84`.
4. Allegheny County row in PNNL-33270 (expected 5A) and EPA radon zone for Allegheny from the PA PDF.
5. WPRDC plumbers CSV field names; City trade-licenses resource id and `license_type_name` values.
6. Overpass count of tagged tradespeople in the county (decides whether OSM existence badges are worth the ODbL attribution).

## 7. Known gaps the product must expose rather than paper over

- **Permit history outside the City of Pittsburgh** — none consolidated; rely on inspection report and owner documents.
- **Equipment age** — not in any public record; onboarding must ask, and "unknown" stays visible.
- **Gutter-cleaning cadence** — no primary source gives an interval ("regularly"); it will be labeled a planning assumption.
- **Local prices** — none licensable; budgets use quotes and labeled assumptions.
- **Workmanship evidence for providers** — none available under any permitted source; the UI will say so.
- **Dye-test rules** — 9 of ~130 municipalities compiled; every row carries a "verify with municipality; last checked" stamp.

## 8. Live verification on the pilot machine (doctor run, 2026-10-29 13:37 UTC, Windows)

11 of 12 endpoints returned HTTP 200 with the documented response shapes: county geocoder (2 candidates with attributes), county parcel point-in-polygon (query works; the test coordinate returned 0 features, i.e. it sits in a right-of-way — the geocoder's PARCELID is the primary path anyway), WPRDC assessments and PLI permits (CKAN `success`/`result.records`), PA DEP radon (SODA count), FEMA NFHL layer 28 (1 feature), DEP MSI layer (1 feature), NRCS SDA POST (`Table` with header+row), NCEI normals, Census geocoder, NWS /points.

**One failure, resolved (12/12 at 13:47 UTC):** PASDA (`mapservices.pasda.psu.edu`) initially failed TLS verification from Python on Windows. Cause: PASDA's certificate chains to "Sectigo Public Server Authentication Root E46", a root in Microsoft's trusted-root program that was not yet in the local Windows root store; Windows apps fetch such roots on demand, Python does not. Fix (no verification bypass): `tools/fix_pasda_tls.py` saved the intermediate to `data/certs/`, then `certutil -urlfetch -verify data\certs\pasda_chain_1.pem` made Windows install the root through its own program. The county's own GIS server hosts only a Parcels open-data service, so PASDA remains the landslide source.

Raw results: `audit/doctor_results.json` (git-ignored; copy kept with the audit on the pilot machine).
