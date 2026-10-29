# Track 2 — Environmental/Hazard Overlays + Municipal Transaction Rules
Audit date: 2026-10-29. Method: WebSearch → WebFetch of official pages. Sandbox limits (egress proxy 403 on curl; robots for hazards.fema.gov and api.weather.gov) are stated as UNVERIFIED with what was tried. Quotes ≤15 words.

## Live tests that worked (plain GET, no credentials)
- NCEI Access Data Service: `https://www.ncei.noaa.gov/access/services/data/v1?dataset=normals-annualseasonal&stations=USW00094823&format=json&dataTypes=ANN-HTDD-NORMAL,ANN-PRCP-NORMAL,ANN-SNOW-NORMAL,ANN-TMIN-PRBFST-T32FP50,ANN-TMIN-PRBLST-T32FP50` → `[{"STATION":"USW00094823","ANN-HTDD-NORMAL":"5710","ANN-SNOW-NORMAL":"414","ANN-TMIN-PRBLST-T32FP50":"04/24","ANN-PRCP-NORMAL":"3819","ANN-TMIN-PRBFST-T32FP50":"10/20"}]` (precip/snow in hundredths/tenths: 38.19 in, 41.4 in; HDD base 65).
- PA DEP radon SODA: `https://data.pa.gov/resource/vkjb-sx3k.json?$select=count(*),max(test_end_date)&county_name=Allegheny` → `[{"count":"359209","max_test_end_date":"2026-10-08T00:00:00.000"}]`. Note county_name is mixed-case `Allegheny` (uppercase returned `[]`).
- PA DEP MSI confirmed-mining ArcGIS point query: `.../MSI_SubsidenceRiskMiningConfirmed/MapServer/0/query?geometry=-80.05,40.375&geometryType=esriGeometryPoint&inSR=4326&outFields=ID&returnGeometry=false&f=pjson` → 1 feature at a South Hills point; 0 at downtown (-80.00,40.44).
- PASDA Allegheny "Landslide Prone 202509": point -80.00,40.44 → 0 features; envelope -80.03,40.42,-79.98,40.45 → 7; total 37 polygons; attributes `code="p"`, `landslidep="Yes"`.

## Tests that failed in sandbox (not evidence of outage)
- api.weather.gov/points — proxy 403 / robots. Docs say /points returns forecast, forecastHourly, forecastGridData, office, stations, zones.
- FEMA NFHL layer 28 point query — proxy 403 / robots. `hazards.fema.gov/robots.txt` disallows `/arcgis` and `/*?*` for crawlers (robots directive, not a ToS prohibition on API clients).
- SDA `Tabular/post.rest` — expects POST; GET rejected. Not verified live.

## 1. FEMA National Flood Hazard Layer (NFHL) — INTEGRATE
- `https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer`; Flood Hazard Zones = layer 28; LOMAs = layer 2; LOMRs = 1; FIRM Panels = 3; NFHL Availability = 0.
- Coverage: national where digital FIRMs exist; Allegheny County countywide FIRM adopted Sept 26, 2014 (municipal page; MSC date UNVERIFIED).
- Fields (layer 28): DFIRM_ID, VERSION_ID, FLD_AR_ID, STUDY_TYP, FLD_ZONE, ZONE_SUBTY, SFHA_TF, STATIC_BFE, V_DATUM, DEPTH, LEN_UNIT, VELOCITY, VEL_UNIT, AR_REVERT, AR_SUBTRV, BFE_REVERT, DEP_REVERT, DUAL_ZONE, SOURCE_CIT, GFID. FLD_ZONE domain: A, AE, AH, AO, AREA NOT INCLUDED, D, OPEN WATER, V, VE, X; SFHA_TF T/F. FIRM Database Technical Reference (Nov 2024): https://www.fema.gov/sites/default/files/documents/fema_rm-firm-database-technical-reference-nov-2024.pdf.
- Access: `/28/query?geometry=lon,lat&geometryType=esriGeometryPoint&inSR=4326&outFields=FLD_ZONE,ZONE_SUBTY,SFHA_TF,STATIC_BFE&returnGeometry=false&f=json`. No key. Point query (not live-verified here).
- Limitations: panel-scale polygons; unmapped areas → no feature / "AREA NOT INCLUDED" / D; LOMAs may remove a structure from SFHA (check layer 2); Zone X still has basement-flooding exposure. WFS limited to 1000 features.
- Update: continuous. Cost: free.
- License: US government work; copyrightText "Federal Emergency Management Agency". OpenFEMA terms ask for citation and a "not endorsed by FEMA" statement (coverage of GIS services UNVERIFIED). Free to view/query; redistribution not prohibited; show disclaimer.
- Risks: robots disallow; TLS 1.2; outages.
- Product decision: flood-zone card + flood-insurance prompt; basement-water/sump/backflow tasks.
- Regional vs verified: zone polygon containment ≠ whether this basement takes water; inspection + seller disclosure item 4 + LOMA are property-level.

## 2. Radon
### 2a. EPA Map of Radon Zones — DEFER (static sentence)
- `https://www.epa.gov/radon/epa-map-radon-zones`; PA PDF `https://www.epa.gov/sites/production/files/2014-08/documents/pennsylvania.pdf`. 1993 county prediction: Zone 1 >4 pCi/L, Zone 2 2–4, Zone 3 <2. EPA: map not for deciding whether individual homes need testing; test every home.
- Allegheny zone: UNVERIFIED from the primary PDF (table unreadable in fetch). PASDA carries "EPA Map of Radon Zones [Pennsylvania] {2021}". Do not state the zone until read from the PDF/PASDA attribute.
- EPA public domain.

### 2b. PA DEP radon test results (data.pa.gov) — INTEGRATE
- Publisher: PA DEP Bureau of Radiation Protection via data.pa.gov (Socrata). Dataset "Radon Test Results September 1986 - Current Annual County Environmental Protection", id vkjb-sx3k, `https://data.pa.gov/d/vkjb-sx3k`; SODA `https://data.pa.gov/resource/vkjb-sx3k.json`. Companion "Radon Mitigation System Year 1987 - Current" id vm4e-6nir (fields include addresspostalcode, municipalityname, latitude/longitude, remediationsystemdesc, systemcost, measurevalue).
- Fields: radon_data_identifier, state_code, address_postal_code, county_code, county_name, municipality_name, radon_test_result_identifier, radon_data_source_name, building_purpose_code, building_type_code, building_sub_type_code, test_floor_level_text, test_method_type_code, mitigation_system_indicator, measure_value (pCi/L), test_start_date, test_end_date, census_tract.
- Size/dates: 3,356,900 rows statewide; 359,209 Allegheny; latest test_end_date 2026-10-08; rowsUpdatedAt 2026-10-20; stated frequency "Annually" (observed more frequent).
- Access: SODA GET JSON/CSV with `$select/$where/$group`; no key for low volume (app token optional; throttle limit unpublished). ZIP aggregation (count, median, % ≥4) straightforward.
- License: "Public Domain"; data.pa.gov policy: free and without restriction; credit requested, not required; as-is.
- Limitations: self-selected tests (not random); ZIP ≠ municipality; building type often "Not Collected"; includes post-mitigation tests. Not a prediction for an individual house.
- Product decision: "Radon: your ZIP's test history" card + test/mitigate task; mitigation-cost context from vm4e-6nir systemcost (labeled).
- Regional vs verified: neighbours' reported tests vs this home's own test.

### 2c. PA DEP certified radon lists — DEFER (link; manual parse)
- See Track 4 §9. Monthly PDFs; URL path embeds month.

### 2d. PA radon disclosure in law
- 68 Pa.C.S. Ch. 73 §7304(b) lists 16 subjects (hazardous substances, basements/crawl spaces, water/sewage, soils/drainage); "radon" not in Ch. 73; appears in Ch. 75 (Home Inspection Law) §7503/§7505.
- 49 Pa. Code §35.335a form (final rulemaking 46 Pa.B. 7638, Dec 10, 2016): radon under item 14 hazardous substances. No radon test required by PA law at sale; only disclosure of seller's knowledge.
- Product decision: testing is voluntary but expected at inspection; cite disclosure item.

## 3. NOAA NCEI U.S. Climate Normals 1991–2020 — INTEGRATE
- DOI 10.25921/4ek7-fk11; metadata `https://www.ncei.noaa.gov/metadata/geoportal/rest/metadata/item/gov.noaa.ncdc%3AC01619/html`; edition 1.0.1 (rev 2023-05-15).
- Access: (1) Access Data Service `https://www.ncei.noaa.gov/access/services/data/v1` — GET, no token (live-verified); datasets normals-annualseasonal, normals-monthly, normals-daily; (2) bulk CSV `https://www.ncei.noaa.gov/data/normals-annualseasonal/1991-2020/access/`; AWS `noaa-normals-pds`; (3) CDO v2 API requires free token — not needed. Rate limits unpublished.
- Station: Pittsburgh International Airport, GHCND USW00094823. Allegheny County Airport USW00014762 (UNVERIFIED id).
- Verified fields: ANN-HTDD-NORMAL 5710 (base 65), ANN-PRCP-NORMAL 38.19 in, ANN-SNOW-NORMAL 41.4 in, first 32°F (50%) Oct 20, last 32°F Apr 24. Monthly: MLY-PRCP-NORMAL, MLY-TMIN-NORMAL, MLY-HTDD-NORMAL.
- License: US government; no warranty; cite DOI. Free to view/query/redistribute.
- Limitations: airport ~15 mi west of downtown; freeze dates are 30-yr probabilities; no microclimate.
- Product decision: seasonal windows (winterize hose bibs before ~Oct 20 median first freeze; gutters before first freeze; AC service before June).

## 4. National Weather Service API — INTEGRATE (with caveats)
- Docs `https://www.weather.gov/documentation/services-web-api`; geolocation guide `https://www.weather.gov/media/documentation/docs/NWS_Geolocation.pdf`.
- Terms: User-Agent required to identify the application (e.g. `(app.example, contact@example)`); no key (may be replaced by key in future); free for any purpose; rate limit not public; retry after ~5 s on 429. Cache /points grid; re-check periodically. GeoJSON default.
- Endpoints: `/points/{lat},{lon}` → forecast links + office/zones; alerts `/alerts/active?zone=PAC003` (Allegheny county UGC = PA + C + 003), `/alerts/active?zone=PAZ021` (public forecast zone "Allegheny", verified from a KPBZ zone forecast product), `/alerts/active?point=lat,lon`. Query by county or point to include county-based warnings.
- License: public domain.
- Risks: undocumented rate limits; 5xx; live /points not run in sandbox.
- Product decision: weather-triggered tasks (freeze warning → disconnect hoses; flood watch → check sump; wind advisory → check gutters). Deferred until core pilot is stable.

## 5. USDA NRCS SSURGO via Soil Data Access — INTEGRATE (POST)
- `https://sdmdataaccess.sc.egov.usda.gov/Tabular/post.rest` (POST; params `query`, `format` = JSON / JSON+COLUMNNAME / JSON+COLUMNNAME+METADATA). Docs: WebServiceHelp.aspx, QueryHelp.aspx, documents/AdvancedQueries.html, documents/TableColumnDescriptionsReport.pdf, Citation.htm.
- Point query: `SDA_Get_Mukey_from_intersection_with_WktWgs84('point(-80.00 40.44)')` then mapunit→component (majcompflag='Yes', order by comppct_r)→chorizon and muaggatt.
- Attributes (confirmed in column descriptions): component.drainagecl, hydricrating, frostact, corcon, corsteel, majcompflag, compname; chorizon.lep_r, hzdept_r; muaggatt.wtdepannmin, drclassdcd, hydclprs, flodfreqdcd, pondfreqprs (muaggatt columns UNVERIFIED in truncated fetch; standard). Allegheny survey area symbol PA003 (UNVERIFIED).
- Limits: max 100,000 rows; no published frequency limit; timeouts possible. No key.
- License: public information; cite "Soil Survey Staff, NRCS, USDA". Free to view/access/redistribute.
- Explicit limitation (NRCS metadata): not a primary regulatory tool; does not eliminate onsite sampling; enlarged maps omit small contrasting areas; scale 1:12,000–1:63,360; urban map units ("Urban land-X complex") common in Pittsburgh with limited attributes.
- Update: annual (date UNVERIFIED).
- Product decision: "Soil & foundation context" card feeding grading/downspout/sump tasks; language says "map unit", not "your lot".

## 6. USDA Plant Hardiness Zone 2023 — DEFER (hard-code label)
- `https://planthardiness.ars.usda.gov/`; GIS/CSV from `https://prism.oregonstate.edu/phzm` (ZIP→zone CSV; 800 m grids; no API).
- Terms (PRISM): OSU retains ownership; freely reproduced/redistributed if USDA-ARS and OSU logos shown on derived maps; altered data need disclaimer; commercial use not addressed.
- Pilot impact: landscaping timing only.

## 7. Termite Infestation Probability — DEFER (static text)
- Source: IRC Table R301.2 / Figure R301.2(6) (ICC copyrighted; do not reproduce). Municipal UCC ordinances state the value locally: Shaler Township (Allegheny County) ecode360: "Termite: Moderate to heavy." and "Frost line depth: 36 inches." Cite the municipal ordinance, not the ICC figure.
- Product decision: static sentence in pests task + seller disclosure item 5 + WDI inspection.

## 8. Wildfire — DEFER/omit
- USFS Wildfire Risk to Communities `https://wildfirerisk.org` (county app JS-rendered; figures UNVERIFIED); downloads via Forest Service Research Data Archive; terms page errored. Not material in Allegheny County.

## 9. Pennsylvania-specific hazards
### 9a. Mine subsidence — INTEGRATE as flag/link (license review before commercial)
- DEP MSI confirmed-mining layer: `https://gis.dep.pa.gov/depgisprd/rest/services/MineSubsidenceInsurance/MSI_SubsidenceRiskMiningConfirmed/MapServer` layer 0; fields OBJECTID, ID, DESCRIPTION, SHAPE.AREA, SHAPE.LEN; Query capability; maxRecordCount 2000. Point query works unauthenticated (verified). Service: areas known to be undermined or near undermined area; DEP recommends MSI coverage. License (iteminfo): "Not for commercial use or resale."; as-is; hold-harmless. © Commonwealth of PA DEP MSI Program.
- PASDA DEP "Mined Out Area – Coal Underground" (DataSummary 257; `https://www.pasda.psu.edu/download/dep/DMO_MinedOutAreaCoalUnderground20261015.zip`; REST `https://mapservices.pasda.psu.edu/server/rest/services/pasda/DEP2/MapServer`; Oct 2026; fields COAL_SEAM, OPERATION, OPERATOR, LASTMINED, OPERATION_STATUS, PERMIT, MAP_SOURCE...). Legacy permit boundaries; not complete. Non-commercial.
- PA Mine Map Atlas `https://www.minemaps.psu.edu/`: historic maps of various/unknown accuracy; no commercial redistribution.
- MSI program FAQ `https://pa.gov/agencies/dep/residents/mine-subsidence-insurance/frequently-asked-questions.html`: homeowners policies usually don't cover subsidence; ~$0.27 per $1,000 coverage; coverage $5k–$1M; application at purchase agreement takes effect at closing; DEP interactive map searchable by address.
- Access: free to view; free to query; NOT for commercial redistribution/resale → prototype shows a derived yes/no flag + link to DEP map; legal review before commercial use.
- Product decision: "Undermined? Consider MSI" card + task "apply for MSI before closing".
- Regional vs verified: map-based confirmation of mining under/near point ≠ parcel-level mine map review or subsidence evidence.

### 9b. Landslide susceptibility — INTEGRATE
- PASDA / Allegheny County "Landslide Prone 202509" (DataSummary 3002; GeoJSON `https://www.pasda.psu.edu/json/AlleghenyCounty__Landslide_Prone202509.geojson`; REST layer 37 of `https://mapservices.pasda.psu.edu/server/rest/services/pasda/AlleghenyCounty/MapServer`; layers 38–40: county landslides, Individual/Public Assistance). 37 polygons; extent covers City of Pittsburgh only (abstract "Pittsburgh Landslide Prone Areas"). Fields: code, acres, sqmiles, landslidep. Derivation criteria UNVERIFIED. Use constraints: informational; as-is. Point query verified; no key.
- SPC "Previously Active Documented Landslides in Southwestern PA" (2017) (DataSummary 1622; REST `.../pasda/SPC/MapServer`; GeoJSON `https://www.pasda.psu.edu/json/SPC_Past_Landslides.geojson`): polygons from 1970s–80s USGS sheets; regional coverage.
- Also: Allegheny County "Slopes201001" (layer 16, >25% slope); USGS Landslide Inventory v3.0.
- Product decision: hillside flag → retaining wall, drainage, downspout discharge tasks.

### 9c. Sewers / lead service lines
- ALCOSAN (`https://www.alcosan.org/our-customers/municipal-customers`): 83 municipalities; municipalities own local sewers; no lateral/dye-test content; no open combined-vs-separate GIS found (UNVERIFIED).
- PWSA lead service line map: `https://experience.arcgis.com/experience/b984ee2a769444049d333beefcf7f7bc` (from `https://www.pgh2o.com/projects-maintenance/lead-line-replacement-programs`). ~83,000 service lines; material confirmed for ~2/3; categories lead/galvanized/unknown; records for 100+-yr-old homes may be outdated; private lead lines replaced at no direct cost. ArcGIS Experience app only (address search); feature-service URL not published → treat as not permitted for automation. PWSA area only.
- Product decision: link-out task "check your service line material"; suburbs → their water authority.

## 10. Municipal point-of-sale sewer dye-test requirements — INTEGRATE (hand-curated table)
No consolidated official list exists (ALCOSAN doesn't publish one; 3RWW 2016 deck is partial). Compiled per municipality from primary sources:

| Municipality | Required at sale? | Source | Who performs | Fee | Lead time | Validity | Fail/escrow | Camera? |
|---|---|---|---|---|---|---|---|---|
| City of Pittsburgh (PWSA) | Yes if in a separate sanitary-sewer area; combined-sewer areas exempt from the test but still need the Evidence of Compliance Certificate | `https://www.pgh2o.com/node/54` (Dye Testing Ordinance, 2006) | Certified plumber/contractor | $20 processing | PWSA replies within 10 business days per step | 3 years | Corrective work + retest | Not stated |
| Mt. Lebanon | Yes (refinance exempt) | `https://mtlebanon.org/residents/public-works/dye-testing/` (Ord. 3099) | Allegheny County–licensed plumber | $50 | Evidence of Compliance ≥10 business days before closing; interim ≥14 | 3 years | Inclement-weather and defects escrow | Not stated |
| Upper St. Clair | Yes; plus lateral video inspection (eff. 1/1/2018) | `https://www.twpusc.org/public-works/sewers` (Ord. 1787, 1998) | Registered plumber | $25 | Forms ≥14 days before closing | 1 year | Repairs before close | Yes |
| Fox Chapel | Yes (sanitary sewer certification) | `https://www.fox-chapel.pa.us/188/Dye-Testing` (Ch. 285 Art. III §285-23) | ACHD-licensed plumber registered with Borough | $425 application; $1,000 weather deposit; $150 return visit | Web: 30 days before closing (ordinance text: 7 days) | 1 year | Defects Agreement + escrow | Yes |
| Dormont | Yes (sale or mortgage) | `https://do1365.zoninghub.com/highlights/procedures/procedure.aspx?id=2114` (§170-29 et seq.) | ACHD-licensed plumber; dye + video | Set by Council | Apply before sale; weather deferral 14 days | Not stated (temp cert 30 days) | $200 weather security; cash security for defects | Yes |
| Scott Township | Yes (sale, transfer, mortgage, refinance; apartments/condos exempt) | `https://scott-twp.com/?p=4165` (Ord. 1427-97) | ACHD-certified plumber | Not listed | Application pickup 5–7 business days | 2 years | Corrections before sale | Not stated |
| Bethel Park | Yes: dye test + camera lateral inspection before deed transfer | `https://www.bethelparkpa.gov/dye-testing` | ACHD-licensed plumber; NASSCO-certified camera contractor | $50 | 21 days before closing | 2 years | Repairs before transfer | Yes |
| Baldwin Borough | Yes (sale or mortgage) | ecode360 Ch. 134 Art. VIII §§134-32…37 | ACHD plumber + video | $25 | 21 days | 5 years | $200 weather / cash security | Yes |
| Homestead Borough | Yes | ecode360 Ord. 1200 (2008) | Registered plumber | Set by Council | 21 days | 10-yr waiver possible | $1,000 security temp cert | Not stated |

Notes: fees/lead times/validity differ widely ($20–$425; 1–5 years); several require lateral camera inspection; nearly all require an ACHD-registered plumber; refinance treatment varies. Any app table must carry "verify with municipality; last checked <date>". ecode360 free to view but not for bulk scraping — store citations and paraphrases.

## 11. PASDA — INTEGRATE (per-dataset terms)
- `https://www.pasda.psu.edu/` (Penn State; free public access). Per-dataset DataSummary pages expose ZIP/KMZ/GeoJSON/CSV downloads and ArcGIS REST at `https://mapservices.pasda.psu.edu/server/rest/services/pasda/<Group>/MapServer` (query; JSON/geoJSON; maxRecordCount 1000 on Allegheny service) + WMS. No key; point queries verified.
- Terms: no site-wide ToS page found; constraints are per-dataset FGDC metadata (county: informational, indemnify; DEP: not for commercial use/resale). As-is.
- Risks: layer names carry date stamps and shift on refresh; mirror hosts exist.

## Summary
| Source | Access | Point query | License | Integrate/Defer | Reason |
|---|---|---|---|---|---|
| FEMA NFHL REST (layer 28) | free; no key (robots for crawlers) | Yes (not live-verified) | US Gov; non-endorsement disclaimer | Integrate | Flood zone → basement/sump/insurance; check LOMA layer |
| EPA Radon Zones | PDF / PASDA | County | Public domain | Defer (static) | DEP data better; zone UNVERIFIED |
| PA DEP radon tests (vkjb-sx3k) | SODA, no key, live-verified | ZIP/municipality/tract | Public Domain | Integrate | 359k Allegheny tests; ZIP stats |
| PA DEP certified radon lists | monthly PDFs | County | Gov directory | Defer (link/manual) | PDF; URL changes monthly |
| PA seller disclosure law / 49 Pa. Code 35.335a | free | n/a | Public law | Integrate (text) | No radon test mandate; items map to tasks |
| NCEI Normals (Access Data Service) | GET JSON, no token, live-verified | Station USW00094823 | Public domain; cite DOI | Integrate | Freeze dates, HDD, precip |
| NWS api.weather.gov | no key; User-Agent; unpublished limits | Yes | Public domain | Integrate later (Checkpoint 7) | Alerts by PAC003/PAZ021 |
| SSURGO via SDA | POST SQL, no key | Yes (WKT point) | Public; not regulatory | Integrate (carefully worded) | Drainage, water table, frost, shrink-swell |
| USDA Plant Hardiness | ZIP CSV | ZIP | OSU conditional | Defer (hard-code) | Landscaping only |
| Termite probability | municipal ordinances | County | Public law; ICC figure © | Defer (static) | "Moderate to heavy" per Shaler ordinance |
| USFS Wildfire | downloads | County | Unclear | Omit | Not material |
| DEP MSI layer | REST, no key, live-verified | Yes | Not for commercial use/resale | Integrate as flag/link (legal review) | Undermined flag + MSI task |
| PASDA DEP Mined Out; Mine Map Atlas | REST + download | Yes | Non-commercial | Defer (link) | Incomplete historic permits |
| PASDA Allegheny Landslide Prone (+SPC) | REST + GeoJSON, live-verified | Yes | County as-is | Integrate | City-only extent; pair with SPC |
| ALCOSAN | web | n/a | n/a | Context only | Confirms municipal regulation |
| PWSA lead line map | Experience app | Address (in-app) | Not stated | Defer (link-out) | PWSA area only |
| Municipal dye-test rules (9 verified) | free to view; no API | Municipality | Public law; ecode360 ToS | Integrate (hand-curated + verify stamp) | No consolidated list |
| PASDA platform | REST + downloads, no key | Yes | Per-dataset | Integrate | Backbone for county/DEP layers |

## Cross-cutting findings
1. Live-verified no-credential GETs: NCEI Access Data Service, data.pa.gov SODA (DEP radon), PASDA/DEP ArcGIS REST point queries. Lowest-risk integrations for a stdlib Windows prototype.
2. DEP MSI risk layer and mined-out areas: "Not for commercial use or resale" — fine for a personal prototype; review before commercial product. Landslide (county) and radon (DEP, Public Domain) have no such restriction.
3. Dye-test rules must be compiled per municipality; City of Pittsburgh has a requirement (sanitary areas; combined areas exempt from test, not certificate).
4. PA law does not require a radon test at sale; only disclosure (item 14).
5. NWS codes: county UGC PAC003; public zone PAZ021.
6. UNVERIFIED to close: live /points shape; FEMA point-query behaviour + MSC date; Allegheny EPA radon zone; SSURGO refresh date / PA003; PWSA feature-service URL/terms; wildfire figures.
