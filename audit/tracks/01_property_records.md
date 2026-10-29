# Track 1 — Property & Parcel Records (Allegheny County, PA)
Audit date: 2026-10-29. Facts read from original portal pages, data dictionaries, or REST endpoints unless marked UNVERIFIED.

## Environment caveat
- In the research sandbox, direct calls to `data.wprdc.org/api/...` were blocked by the sandbox egress proxy, and WPRDC's `robots.txt` disallows `/api/` and `/datastore/dump/` for crawlers. So the live `datastore_search?limit=1` call is UNVERIFIED here. The robots.txt comments say the API is excluded for crawlers only to reduce crawl cost and that people may use it from their own code; crawl-delay 10s; contact wprdc@pitt.edu for heavy automated use. Re-run the live test on the Windows machine in Checkpoint 2.
- Documented query patterns (from `https://data.wprdc.org/datastore/api_info/65855e14-549e-4992-b5be-d629afc676fa`):
  - `GET https://data.wprdc.org/api/action/datastore_search?resource_id=65855e14-549e-4992-b5be-d629afc676fa&limit=5`
  - `GET ...datastore_search?resource_id=...&q=<text>`
  - `POST datastore_search` JSON body `{"resource_id": "...", "filters": {...}}`
  - `GET https://data.wprdc.org/api/action/datastore_search_sql?sql=SELECT * from "65855e14-549e-4992-b5be-d629afc676fa" WHERE ...` (alias `property_assessments_table`)
  - Standard CKAN response shape: `{"success": true, "result": {"fields": [...], "records": [...], "total": N}}` (not verified live).
  - Street filter that should work (untested): `filters={"PROPERTYHOUSENUM":"414","PROPERTYADDRESS":"GRANT ST"}` — whether PROPERTYADDRESS includes the suffix is UNVERIFIED.
  - No rate limits stated.

## 1. WPRDC — Allegheny County Property Assessments
- Publisher: Allegheny County (Office of Property Assessments), hosted by WPRDC. `https://data.wprdc.org/dataset/property-assessments`
- Resources: API/datastore table `65855e14-549e-4992-b5be-d629afc676fa` (data last updated Oct 7, 2026); bulk CSV `9a1c60bd-f9f7-4aba-aeb7-af8c3aaa44e5` (`.../download/assessments.csv`); data dictionary CSV `c665470c-ee72-4f0d-b772-4f09c2145f2a`; user guide PDF `cc4bafd2-25b6-41d7-83aa-d16bc211b020`.
- Coverage: all parcels, county-wide, parcel level.
- Fields (86, from the data dictionary): PARID, PROPERTYHOUSENUM, PROPERTYFRACTION, PROPERTYADDRESS, PROPERTYCITY, PROPERTYSTATE, PROPERTYUNIT, PROPERTYZIP, MUNICODE, MUNIDESC, SCHOOLCODE, SCHOOLDESC, LEGAL1-3, NEIGHCODE, NEIGHDESC, TAXCODE/DESC, TAXSUBCODE(_DESC), OWNERCODE/DESC, CLASS/CLASSDESC, USECODE/USEDESC, LOTAREA, HOMESTEADFLAG, CLEANGREEN, FARMSTEADFLAG, ABATEMENTFLAG, RECORDDATE, SALEDATE, SALEPRICE, SALECODE, SALEDESC, DEEDBOOK, DEEDPAGE, PREVSALEDATE(2), PREVSALEPRICE(2), CHANGENOTICEADDRESS1-4, COUNTYBUILDING/LAND/TOTAL, COUNTYEXEMPTBLDG, LOCALBUILDING/LAND/TOTAL, FAIRMARKETBUILDING/LAND/TOTAL, STYLE, STYLEDESC, STORIES, YEARBLT, EXTERIORFINISH, EXTFINISH_DESC, ROOF, ROOFDESC, BASEMENT, BASEMENTDESC, GRADE, GRADEDESC, CONDITION, CONDITIONDESC, CDU, CDUDESC, TOTALROOMS, BEDROOMS, FULLBATHS, HALFBATHS, HEATINGCOOLING, HEATINGCOOLINGDESC, FIREPLACES, BSMTGARAGE, FINISHEDLIVINGAREA, CARDNUMBER, ALT_ID, TAXYEAR, ASOFDATE. No owner-name field.
- Code lookups in the dictionary: BASEMENT 1=None, 2=Slab/Piers, 3=Crawl, 4=Part, 5=Full. CONDITION 1=Excellent, 2=Good, 3=Average, 4=Fair, 5=Poor, 6=Unsound, 7=Very good, 8=Very poor. GRADE A/X/XX, B, C, D, E (± modifiers). CDU, HEATINGCOOLING, ROOF, EXTERIORFINISH, STYLE codes are NOT fully enumerated → rely on *DESC columns.
- Caveats (user guide): living area estimated from exterior measurement; interior access not routine; how YEARBLT is derived is not documented (UNVERIFIED); assessed ≠ market value.
- Update: data changes daily; published monthly.
- Access: bulk CSV; CKAN datastore API (search, filters, SQL). Query by address (PROPERTYHOUSENUM + PROPERTYADDRESS) or PARID. No lat/lon → no point query.
- Cost: free; no stated limits.
- License: Creative Commons CC0 (`http://www.opendefinition.org/licenses/cc-zero`). Portal Data Use Agreement (`https://data.wprdc.org/about`): as-is, no warranty, user indemnifies; dataset license governs. Attribution not legally required under CC0; attributing "Allegheny County via WPRDC" is best practice. WPRDC attribution page UNVERIFIED (robots-blocked).
- Redistribution/commercial/caching: permitted (CC0) — free to view, programmatic, redistribute.
- Risks: monthly snapshot lag; code tables incomplete; datastore preview was "not available" on the resource page (possible flakiness); keep polite request rate or cache CSV locally.
- Supports: core house profile (age, basement, stories, exterior, roof, heating category, condition/CDU, grade, fireplaces, basement garage, lot area, living area).

## 2a. WPRDC — Allegheny County Parcel Boundaries
- `https://data.wprdc.org/dataset/allegheny-county-parcel-boundaries1`; publisher Allegheny County GIS; PASDA is source of record.
- Resources: GeoJSON `3f50d47a-ab54-4da2-9f03-8519006e9fc9`; CSV datastore `858bbc0f-b949-4e22-b4bb-1a78fef24afc` (Oct 22, 2026); Shapefile; KMZ; Esri REST `https://maps.pasda.psu.edu/ArcGIS/rest/services/pasda/AlleghenyCounty/MapServer/25`.
- CSV fields: pin, map_block_lot, municode, calc_acreage, comments, notes, pseudono, shape_length, wkt. CRS: PA State Plane South (ft), WKID 102729/2272 → offline point-in-polygon needs reprojection; use REST with inSR=4326 instead.
- Update: as needed / monthly (PASDA metadata: weekly).
- License: "License not specified" on WPRDC; PASDA: informational use only, as-is. → Free to view and query; redistribution rights UNVERIFIED.
- No address fields → address→parcel needs §2b or §7.

## 2b. WPRDC — Allegheny County Addressing Address Points
- `https://data.wprdc.org/dataset/allegheny-county-addressing-address-points2`; publisher Allegheny County; PASDA authoritative.
- Resources: CSV datastore `ddc46dc5-65bf-42d2-b67d-dd45954b25da` (Oct 27, 2026); GeoJSON `492a62fb-0560-43f0-9f8e-037fc51343a0`; Shapefile; KMZ; Esri REST `.../pasda/AlleghenyCounty/MapServer/32`.
- Fields (35) include ADDRESS_ID, PARENT_ID, ADDRESS_TY, STATUS, ADDR_NUM, ST_PREFIX, ST_NAME, ST_TYPE, UNIT, MUNICIPALI, ZIP_CODE, FULL_ADDRE, PARCELID, geometry (text; State Plane; no separate lat/lon columns).
- Address → parcel ID without GIS libs: YES via plain CSV join on FULL_ADDRE/ADDR_NUM/ST_NAME/MUNICIPALI → PARCELID. Coordinates need parsing the geometry column (format UNVERIFIED) and reprojection.
- Update: as needed / monthly. License: "License not specified".

## 3. WPRDC — Allegheny County Property Sale Transactions
- `https://data.wprdc.org/dataset/real-estate-sales`; main CSV datastore `5bbe6c55-bce6-4edb-9d04-68edeb6bf7b1` (Oct 28, 2026); yearly resources 2012–2026.
- Coverage: county-wide, 2012–present. Update: daily.
- Fields (25): PARID, FULL_ADDRESS, PROPERTYHOUSENUM, PROPERTYFRACTION, PROPERTYADDRESSDIR, PROPERTYADDRESSSTREET, PROPERTYADDRESSSUF, PROPERTYADDRESSUNITDESC, PROPERTYUNITNO, PROPERTYCITY, PROPERTYSTATE, PROPERTYZIP, SCHOOLCODE/DESC, MUNICODE/DESC, RECORDDATE, SALEDATE, PRICE, DEEDBOOK, DEEDPAGE, SALECODE, SALEDESC, INSTRTYP, INSTRTYPDESC. No owner fields.
- Sale validation: SALECODE is a subjective validity category that can change after review; multi-parcel deeds typically coded "H" (invalid). Full code list UNVERIFIED (referenced dictionary not found); filter on SALEDESC text ("valid").
- Recording lag: several weeks. License: CC0.
- Supports: closing-date/price confirmation and prior sales; low priority (user knows their closing date).

## 4. Allegheny County Real Estate Portal
- `https://realestate.alleghenycounty.us/` → `Search.aspx`. Search by address or parcel number; no owner-name search. Tabs: General, Building, Tax, Owner History, Image, Comparables, Appeal Status, Maps. Updated daily (fresher than WPRDC).
- Terms: county "Disclaimers and Privacy Policy" (`https://www.alleghenycounty.us/Site-Footer/Disclaimers-and-Privacy-Policy`): commercial use strictly prohibited without written consent; county retains rights; use monitored. No API; ASP.NET postbacks.
- Classification: free to view only. Recommendation: deep-link for users to verify; do not scrape.

## 5. Building permits
- City of Pittsburgh PLI Permits (WPRDC): `https://data.wprdc.org/dataset/pli-permits`; resource `f4d1177a-f597-4c32-8cbf-7885f56253f6` (Oct 29, 2026). Coverage: City of Pittsburgh only, permits from 2019-06-01; building/mechanical/electrical/general; plumbing excluded. Update daily. Unit: parcel.
  - Fields (18): permit_id, permit_type, owner_name, contractor_name, work_description, work_type, commercial_or_residential, total_project_value, issue_date, parcel_num, address, latitude, longitude, council_district, neighborhood, ward, zip_code, status. Contains owner_name — do not surface. One permit may span multiple rows.
  - License: CC-BY (attribute City of Pittsburgh).
  - Query: parcel_num (format match with PARID UNVERIFIED), address, lat/lon.
  - Risk: feed recently switched; some fields being restored.
- County-wide permit source: none found. Permits are issued per municipality (130 municipalities); no consolidated open dataset. County ArcGIS FeatureServers named `Commercial_Permits`, `FSP_Permits` etc. exist (contents/currency UNVERIFIED, apparently commercial/2018-era). → Permit history is a gap outside the City; rely on inspection report + owner input.

## 6. WPRDC — Allegheny County Plumbing Inspections & Violations
- `https://data.wprdc.org/dataset/allegheny-county-plumbing-inspections`; ACHD; CC0; county-wide; 2016-12-14/present.
- Resources: Inspections `a3fb93b8-01a3-4090-8e8e-6310a4160071` (Aug 5, 2026); 2016–2025 `89481a55-2d81-4bb9-9e46-2fd4a3aab0ac`; Violations `e4ac2f5d-f22d-45fd-a844-88cb3c706401`.
- Status: effectively suspended — 07/29/2026 notice: undercounting after an Oct 2025 software transition; updates suspended pending a new solution; "Not Updated (Historical Only)".
- Fields (20) include inspection_date, address, city, zip_code, municipal, building_type, plumber_name, final_insp_yn, storm_drain, building_drain, water_service, storm_sewer, rough_above_ground, water_heater, building_sewer, water_distribution, indirect_waste. No parcel ID, no lat/lon.
- Recommendation: defer; at most a historical hint with a staleness warning.

## 7. Allegheny County GIS / ArcGIS REST
- County-hosted: `https://gisdata.alleghenycounty.us/arcgis/rest/services` (folders: Accela, ACWebsite, Addressing, DPW, EGIS, Geocoders, LandRecords, Network, OPENDATA, Routing, Utilities).
  - `LandRecords/Parcel_Features/MapServer/0` — parcel polygons; Query capability; JSON/geoJSON; maxRecordCount 1000; WKID 2272; fields PIN, MAPBLOCKLOT, MUNICODE, CALCACREAGE, NOTES, PSEUDONO, COMMENTS, MODIFIED*, CREATED*, GlobalID, OBJECTID, SHAPE.
  - Point-in-polygon by lat/lon: VERIFIED WORKING — `.../Parcel_Features/MapServer/0/query?geometry=-79.935,40.455&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelWithin&outFields=PIN,MUNICODE&f=json` → 1 feature (PIN 0051P00325000900, MUNICODE 107).
  - `Geocoders/AddressVerification/GeocodeServer/findAddressCandidates?SingleLine=414%20Grant%20St%20Pittsburgh&outSR=4326&maxLocations=1&outFields=*&f=json` — VERIFIED: score 100, lat/lon, Addr_type=PointAddress, attributes include PARCELID, SCHOOLDISTRICT, ZIP_CITY. Simplest zero-dependency address → parcel ID + coordinates path. `outFields=*` required. `Geocoders/AddressSearch` is a centerline locator the service says not to use for verification.
- PASDA mirror `.../pasda/AlleghenyCounty/MapServer/25` (parcels 202610; maxRecordCount 2000): same point query VERIFIED. Default spatialRel returned nothing; `esriSpatialRelWithin` works; MUNICODE is numeric in `where`.
- ArcGIS Online `https://services1.arcgis.com/vdNDkVykv9vEWFX4/ArcGIS/rest/services/AlCoParcels/FeatureServer/0` — parcels joined with 147 assessment attributes but lastEditDate ≈ 2022-06-17 and includes owner fields → stale; do not use.
- Terms: no copyrightText on services; county GIS privacy/disclaimer (`https://apps.alleghenycounty.us/gis/privacy_policy.html`): commercial use/sale prohibited without written consent; as-is. No rate limits or scraping clause published. → free to view and query programmatically; commercial redistribution requires consent; caching for a non-commercial prototype is low-risk but not formally confirmed.

## Summary
| Source | Access | Point/address query | License | Recommend | Reason |
|---|---|---|---|---|---|
| WPRDC Property Assessments | CSV + CKAN API (API untested in sandbox) | address filters, PARID; no lat/lon | CC0 | Integrate (primary) | All needed building-characteristic fields; redistributable |
| WPRDC Parcel Boundaries | GeoJSON/CSV(WKT)/SHP + PASDA REST | REST point-in-polygon (inSR=4326, Within) | Not specified | Integrate via REST only | Only needed to map a pin to a PIN |
| WPRDC Address Points | GeoJSON/CSV + PASDA REST | address→PARCELID via CSV join | Not specified | Integrate as offline fallback | Zero-dependency address→parcel |
| WPRDC Sale Transactions | CSV + CKAN API | PARID/address | CC0 | Defer (optional) | Lag; code list unpublished |
| County Real Estate Portal | Web only | manual search | County disclaimer: no commercial use | Link-out only | Freshest data; no API |
| Pittsburgh PLI Permits | CSV + CKAN API | parcel_num, address, lat/lon | CC-BY | Integrate (City of Pittsburgh only) | 2019+ permit history; county-wide gap |
| County Plumbing Inspections | CSV | address string | CC0 | Defer | Suspended Jul 2026; undercounting |
| County ArcGIS REST | ArcGIS REST JSON | VERIFIED lat/lon→PIN; address→PARCELID+lat/lon | No license stated; non-commercial disclaimer | Integrate (lookup layer) | One GET resolves address to parcel |
| ArcGIS Online AlCoParcels | ArcGIS REST | yes | "custom"/informational | Defer | Stale (2022), owner names |

## Recommended zero-dependency pipeline
1. Address → county `AddressVerification` geocoder (`outFields=*`, `outSR=4326`) → PARCELID + lat/lon (verified).
2. PARCELID → WPRDC `datastore_search` with `filters={"PARID": "<id>"}` (re-verify live on Windows). Fallback: download `assessments.csv` once and index by PARID locally (CC0).
3. If MUNIDESC is City of Pittsburgh → PLI permits by `parcel_num` (CC-BY).
4. Pilot filter: `YEARBLT < 1960 AND BASEMENT IN ('4','5')`; display *DESC strings.

## Open items / UNVERIFIED
- Live `datastore_search` response and `filters` syntax.
- Full SALECODE list; CDU/HEATINGCOOLING/ROOF/EXTERIORFINISH/STYLE code tables.
- WPRDC attribution page text; parcel/address-point redistribution license.
- PLI `parcel_num` vs assessments `PARID` format.
- Address-points CSV `geometry` column format.
- Formal rate limits on gisdata.alleghenycounty.us / data.wprdc.org (none published).
