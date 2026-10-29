# Track 4 — Provider Inventory/Verification + Geocoding
Audit date: 2026-10-29. Method: WebSearch → WebFetch of official pages. Research-sandbox note: the egress proxy blocked direct curl to geocoding.geo.census.gov, nominatim, overpass-api.de and data.wprdc.org, and the fetch proxy honors robots.txt, so some live tests could not run; those are marked UNVERIFIED, not guessed.

## GEOCODING

### 1. US Census Bureau Geocoder
- Publisher: US Census Bureau. Base `https://geocoding.geo.census.gov/geocoder/{locations|geographies}/{onelineaddress|address|coordinates}`; batch `/locations/addressbatch` (10,000 records/file). Docs: `https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.pdf`.
- Fields: matchedAddress, coordinates{x,y}, tigerLine{tigerLineId, side}, addressComponents{fromAddress,toAddress,streetName,...}; `geographies` adds State, County, Tract, Block.
- Access: HTTPS GET, `format=json`, no API key. `benchmark=Public_AR_Current`, `vintage=Current_Current`.
- Accuracy: interpolated along TIGER address ranges (not rooftop).
- Live test (locations/onelineaddress, "710 Washington Rd Pittsburgh PA 15228"): matched `710 WASHINGTON RD, PITTSBURGH, PA, 15228`; x=-80.045318, y=40.379364; tigerLineId 658055863, side R; range 696–714. The `geographies` return type errored through the proxy on four attempts — UNVERIFIED live (documented in PDF).
- Rate limits: none stated in PDF; general Census API ToS says use may be subject to limitations. No numeric limit found.
- Benchmarks updated twice yearly. Cost: free. Terms: US federal public data; include the Census Data API attribution/non-endorsement line to be safe. Automated access: permitted (batch endpoint exists).
- Risks: intermittent server errors (observed); interpolated positions can land on the wrong parcel — good enough for municipality/service-area, not for parcel matching.
- App wording: "Approximate location (US Census TIGER street-range match)".

### 2. OpenStreetMap Nominatim (public instance)
- `https://nominatim.openstreetmap.org/search?q=...&format=jsonv2&addressdetails=1`; `/reverse`. Usage policy: `https://operations.osmfoundation.org/policies/nominatim/`.
- Policy (verified): max 1 request/second; valid identifying User-Agent/Referer required (stock library UAs not acceptable); no autocomplete; no bulk/systematic queries; cache results on your side; scheduled scripts ≤4 req/min; services whose primary function is geocoding must run their own instance; access may be withdrawn at any time. The policy asks that any LLM-generated recommendation link the policy prominently — do so in the README.
- License: ODbL 1.0; attribution "© OpenStreetMap contributors" linked to openstreetmap.org/copyright.
- Live test: BLOCKED in sandbox (robots/egress). Documented fields: place_id, osm_type, osm_id, lat, lon, display_name, address{...}, licence.
- Accuracy: building-level where OSM has address nodes; Allegheny County house-number coverage UNVERIFIED.
- Automated access: permitted only within policy; fine for pilot volume; not as primary geocoder.
- Wording: "Location via OpenStreetMap (© OpenStreetMap contributors, ODbL)".

### 3. Allegheny County address points (offline geocoder)
- Publisher: Allegheny County GIS; addresses assigned by municipalities. PASDA `https://www.pasda.psu.edu/uci/DataSummary.aspx?dataset=1219` ("Allegheny County - Address Points (2026)"); county ArcGIS Hub `https://openac-alcogis.opendata.arcgis.com/datasets/626854df63a84eeaa2b3fca9b0a3b911`; WPRDC mirror (see Track 1 §2b, which found a PARCELID field in the WPRDC CSV).
- Downloads (verified on PASDA): ZIP shapefile `https://www.pasda.psu.edu/download/alleghenycounty/AlleghenyCounty_AddressPoints20261026.zip`; GeoJSON `https://www.pasda.psu.edu/json/AlleghenyCounty_AddressPoints202610.geojson`; ArcGIS REST `https://mapservices.pasda.psu.edu/server/rest/services/pasda/AlleghenyCounty/MapServer` layer 32 (parcels layer 25; municipal boundaries layer 21).
- Size: 474,492 point features (PASDA metadata); file size UNVERIFIED (expect tens of MB GeoJSON). PASDA metadata fields: ADDR_NUM, ST_PREFIX, ST_NAME, ST_TYPE, ST_SUFFIX, ZIP_CODE, MUNICIPALI, FULL_ADDRE, OBJECTID, Shape. (Track 1 found PARCELID in the WPRDC CSV version — reconcile at load time.)
- Update: monthly to PASDA; weekly Hub harvest.
- License/terms: as-is disclaimer only; no explicit licence (UNVERIFIED). Do not assume CC0.
- Feasibility: YES — download GeoJSON once, normalize FULL_ADDRE, index in dict/SQLite; exact-match yields point-level coordinates for ~474k addresses, no rate limits.
- Risks: field names may vary by release; postal city vs MUNICIPALI mismatch (e.g., "Pittsburgh" vs Mt. Lebanon).
- Wording: "Address matched to Allegheny County address-point data (<file date>)".

## PROVIDER SOURCES

### 4. OpenStreetMap Overpass API
- Public instance `https://overpass-api.de/api/interpreter`; usage doc `https://dev.overpass-api.de/overpass-doc/en/preface/commons.html`.
- Limits (verified): ~10,000 requests/day and <1 GB/day per user; per-IP slots with cool-down; 429 when denied; timeout 180 s. Discouraged: repeating queries at scale, stitching bboxes to scrape, building a non-OSM app on the public instance.
- Tags: craft=plumber, craft=electrician, craft=roofer, craft=hvac (approved), craft=carpenter, craft=painter, craft=chimney_sweep (UNVERIFIED as documented), shop=plumbing.
- Live count for Allegheny County: NOT OBTAINED (robots/egress). Expectation: sparse (tens). Test query from Windows: `[out:json];area[name="Allegheny County"][admin_level=6]->.a;(nwr[craft=plumber](area.a);nwr[craft=electrician](area.a);nwr[craft=hvac](area.a);nwr[craft=roofer](area.a););out tags;`
- License: ODbL 1.0 — attribution required; republishing a substantial POI extract is a Derivative Database under ODbL. Commercial use permitted.
- Evidence category: EXISTENCE only. Wording: "Listed in OpenStreetMap as <craft> (© OpenStreetMap contributors)".

### 5. PA Attorney General — HICPA registration search
- Info `https://www.attorneygeneral.gov/?p=3456` (= /home-improvement-contractor-registration/); search `https://hicsearch.attorneygeneral.gov/`; AG press release 2026-05-06 on the new dashboard.
- Status today: RESTORED. Info page: effective April 24, 2026 the online registration system is operational. Press release: cyber incident Aug 2025 disabled online registration; searchable status restored March 2026; HelpLine since Nov 2025; grace period for unregistered contractors ended June 8, 2026. Search app loaded with no outage banner.
- Search fields: "Registration Number" named in page text; other filters UNVERIFIED. Results show ACTIVE registrations only; per-record "Redacted Business Report" PDF; export to Excel. Expiration/insurer columns UNVERIFIED.
- Insurance: HICPA §4(a)(1)(ix) requires proof of liability insurance ≥ $50,000 personal injury / $50,000 property damage at registration. Whether search displays insurer: UNVERIFIED.
- Automated/bulk: no ToS, robots statement, API or bulk list found; Excel export is per-search. Treat automated scraping as NOT PERMITTED by default. Right-to-Know request is the legitimate bulk route (UNVERIFIED precedent).
- Phone: 1-888-520-6680; hic@attorneygeneral.gov.
- Proves: ≥$5,000/yr contractor filed registration, paid $100/2 yrs, attested ≥$50k/$50k insurance at filing; number must appear in ads (§6). Does NOT prove competency, skill, or current insurance. PA has no contractor license; AG never uses the word "license".
- Evidence category: REGISTRATION (+ insurance-at-filing). Wording: "Registered with the PA Attorney General under HICPA, PA#######, as of <date checked>". Never "licensed" or "insured".
- Integration: DEFER automation; store manually checked number + date + link.

### 6. ACHD Registered Master Plumbers / WPRDC "Allegheny County Plumbers"
- ACHD search `https://eapps.alleghenycounty.us/Plumbing`: fields Last Name, First Name, HP ID (5-digit), Zip; empty search lists all registered master plumbers. Result columns/status UNVERIFIED. No ToS; automated access neither granted nor prohibited — avoid heavy use.
- WPRDC `https://data.wprdc.org/dataset/allegheny-county-plumbers`: resources "PlumbersCSV" (`60637ef7-96c9-47ee-95c3-ccc2a2140367`) and "Plumbers (2015-2025) CSV" (`e8e2e1a7-8a06-4d69-8a0d-12f9e4e99b86`); CC0; CKAN API available; field names UNVERIFIED (robots-blocked). Publishing frequency now "Not Updated (Historical Only)"; 07/29/2026 note: updates suspended after software transition caused undercounting; list derived from inspection records, so active plumbers with no recently inspected work may be absent.
- Proves (ACHD Plumbing Program page, exam application, County Code Ch. 860): county-wide licensing under Plumbing Code Article XV (2009 IPC as amended); master license needs journeyman license, 2 yrs under a master, exam (75%), fees, annual renewal; only a registered master plumber (or owner-occupant) may pull a plumbing permit. Insurance/bond: NOT found — do not claim.
- Evidence category: LICENSING (exam-based) + task suitability for plumbing permits. Wording: "Allegheny County Health Department registered master plumber, HP #####, verified <date>".
- Integration: INTEGRATE CC0 CSV as seed list with staleness warning + manual re-check link.

### 7. Electricians
- City of Pittsburgh PLI Electrical Trade License: required for electrical work within the City; issued to individuals; ICC master electrician exam; annual renewal with 8 CEU hours; $1M/$2M GL + workers' comp required to pull permits, not for the license itself. No public lookup on the page.
- WPRDC "Licensed Businesses, Contractors & Trades" (`https://data.wprdc.org/dataset/business-contractors-trades`), City of Pittsburgh, CC0, weekly, 2011–present; resources Business Licenses, Licensed Contractors, Trade Licenses. Business Licenses dictionary includes license_number, license_type_name, business_name, address, license_state (Active/Expired), issue/effective/expiration dates, insurance_expiration_date, parcel_number, naics_code. Trade Licenses resource id and whether license_type_name includes "Electrical": UNVERIFIED.
- Suburbs: NO county-wide and NO state-wide electrician license. PA BPOA lists 29 boards; none covers electricians, plumbers, HVAC or contractors (verified). Municipal registration varies per municipality; unaggregated.
- Evidence category: LICENSING (City only) + insurance expiry date field. Wording: "City of Pittsburgh electrical trade license #, status <Active>, per City open data <date>"; suburbs: "PA has no state electrician license; check your municipality".
- Integration: INTEGRATE CC0 CSV; label City-only scope.

### 8. HVAC
- No PA state HVAC license (BPOA list) — confirmed; no county HVAC license found (UNVERIFIED negative). HICPA registration is the only state-wide hook.
- EPA Section 608: tests administered by EPA-approved certifying organizations; EPA does not issue cards; no EPA public lookup. NATE offers a downloadable 608 spreadsheet (dated Sept 2024, stale) and ID lookup; reuse terms UNVERIFIED.
- NATE certification: natex.org verification requires technician NATE ID.
- Evidence category: individual certification, not programmatically verifiable. Wording: "Technician states EPA 608 certification (not verified by HomeKeeper)". DEFER.

### 9. Radon — PA DEP certified testers/mitigators
- `https://www.pa.gov/agencies/dep/programs-and-services/radiation-protection/radon-division/radon-services-directory.html`. Six PDFs under `https://files.dep.state.pa.us/RadiationProtection/RadonDivision/RDPortalFiles/2026/10_01/`: WebTestAlpha.pdf, CountyTest.pdf, WebMitigationAlpha.pdf, CountyMitigation.pdf, WebLabAlpha.pdf, CountyLab.pdf. Updated monthly; lists dated Oct 1, 2026; folder path changes monthly (YYYY/MM_01).
- Format: PDF only. Stdlib parsing hard; one-time manual extraction of Allegheny rows is realistic for the pilot.
- Proves: DEP certification under the Radon Certification Act (DEP ID numbers; 7000-series mitigation, 8000-series testing). Page advises checking for a current DEP ID card. Insurance: not stated.
- Terms: Commonwealth public data; no reuse restriction stated.
- Evidence category: CERTIFICATION (state). Wording: "PA DEP certified radon <tester/mitigator>, DEP ID #, per DEP list dated <date>". INTEGRATE (manual/monthly).

### 10. Chimney — CSIA directory
- `https://web.csia.org/CSIA-Certified` (state pages e.g. /CSIA-Certified/Pennsylvania). Radius search; listings show credential type, business, address, phone; no expiration dates. Free to view; "intended as a public service"; not for marketing/business development. No API; search endpoint robots-disallowed. Automated access: assume NOT permitted.
- Evidence category: private certification. Wording: "Listed as CSIA Certified Chimney Sweep on csia.org as of <date>" (manual). DEFER automation.

### 11. BBB
- Terms: content for personal, non-commercial use; not for republication or aggregation; may not compile data for any application. No API. Redistributing BBB ratings: NOT PERMITTED. Link out only.

### 12. Google Places API (New)
- Pricing page dated 2026-10-28: monthly free calls per SKU tier — Essentials 10,000, Pro 5,000, Enterprise 1,000. Nearby Search Pro $32/1,000; Text Search Pro $32/1,000; Place Details Essentials $5/1,000, Pro $17/1,000, Enterprise $20/1,000. Requires billing-enabled GCP account + API key.
- Terms: no scraping/export of Maps Content; place IDs storable indefinitely; lat/lon cacheable ≤30 days; no display on non-Google maps; Google attribution required; may not copy and save business names/addresses/reviews.
- Conclusion: unnecessary — key/billing required; forbids storing the provider list; evidence weaker than public registries. DEFER.

### 13. Yelp Fusion API
- Pricing: Base $229/mo, Enhanced $299/mo, Premium $643/mo; 30-day trial 5,000 calls; no free tier. Caching/attribution terms UNVERIFIED (robots-blocked). DEFER.

### 14. Marketplaces
- Angi/HomeAdvisor: ToS bars scrapers/robots; no public API. Not usable.
- Thumbtack: ToS bars automated tools; gated partner developer program. Not usable.

## Summary
| Source | Evidence category | Access | Automated OK? | License | Integrate/defer | Reason |
|---|---|---|---|---|---|---|
| Census Geocoder | geocoding (interpolated) | HTTPS JSON, no key | Yes | US public | Integrate (fallback) | Free; intermittent errors |
| Nominatim | geocoding | HTTPS JSON, no key | ≤1 req/s, custom UA, cached | ODbL | Integrate (last resort) | Policy forbids heavy/primary use |
| Allegheny address points | geocoding (point-level) | GeoJSON/SHP, REST | Yes (download once) | as-is; no explicit license | Integrate (primary offline) | 474k points; no limits |
| Overpass/OSM | existence | HTTPS, no key | Within ~10k/day | ODbL share-alike | Integrate (low priority) | Likely sparse; existence only |
| PA AG HICPA search | registration | Web UI, Excel export; phone | No grant → no | Public record | Integrate manually | Restored Apr 2026; only statewide credential |
| ACHD plumbers + WPRDC CSV | licensing | Web; CC0 CSV | Yes (CSV) | CC0 | Integrate | True license; dataset frozen Jul 2026 |
| City of Pittsburgh licenses (WPRDC) | licensing (city) + insurance expiry | CC0 CSV weekly | Yes | CC0 | Integrate | Only electrician credential; city scope |
| Suburban electricians | none | — | — | — | N/A | No state/county license |
| EPA 608 / NATE | certification (individual) | ID lookup / stale XLSX | No | UNVERIFIED | Defer | No name lookup |
| PA DEP radon lists | certification (state) | Monthly PDFs | Yes (monthly) | Public | Integrate (manual parse) | Authoritative; PDF only |
| CSIA directory | private certification | Web UI | No | Proprietary | Defer (link) | No API |
| BBB | none | Web | No | Non-commercial only | Do not use | Aggregation prohibited |
| Google Places (New) | existence/reviews | key + billing | Storage prohibited | Proprietary | Defer | Key required; can't store list |
| Yelp Fusion | existence/reviews | Paid | Paid | Proprietary | Defer | Paid |
| Angi / Thumbtack | — | None | Prohibited | Proprietary | Do not use | Scraping banned |

## Recommended provider-evidence approach (prototype)
1. Geocode via the county AddressVerification geocoder (Track 1, verified; returns PARCELID) with the address-point GeoJSON as offline fallback, then Census, then Nominatim (1 req/s, custom UA, cached). Label municipality from PASDA layer 21 — drives City vs suburb credential logic.
2. Seed providers only from licensed/registered public lists: ACHD master plumbers CSV (CC0, "list frozen 2026-07-29"), City of Pittsburgh trade/contractor licenses CSV (CC0, weekly), PA DEP radon PDFs (manual Allegheny extract, dated). Not from OSM/Google/Yelp/marketplaces as evidence.
3. Per provider, store evidence records {source, identifier, status, date_checked, url}. Render only literal dated wording. "Licensed" only for ACHD plumbers, City of Pittsburgh trade licenses, DEP radon certification; "insurance" only as "insurance expiration date on file: <date>" (City data) or "HICPA requires $50k/$50k liability insurance at registration".
4. HICPA verification manual: "Verify" link to hicsearch + HelpLine number + form to record number/date confirmed.
5. Workmanship/quality evidence: none available under these terms; say so in the UI.

## UNVERIFIED (test from Windows)
- Overpass counts; Census geographies return; Nominatim live response.
- WPRDC plumbers CSV field names; Trade Licenses resource id / license_type_name values.
- hicsearch result columns; its robots.txt.
- Address-point file size and license.
- CSIA full terms; Yelp caching terms; ACHD insurance/bond requirement.
