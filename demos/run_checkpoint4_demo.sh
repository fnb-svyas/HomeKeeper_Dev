#!/bin/sh
# Regenerates demos/checkpoint4_demo_output.txt (synthetic sample; safe to re-run).
cd "$(dirname "$0")/.." && rm -f houses/sample-complete.json
H=homekeeper.py
python3 $H sample complete > /dev/null
python3 $H answer sample-complete heating_fuel gas > /dev/null
python3 $H answer sample-complete heating_type "forced air" > /dev/null
python3 $H answer sample-complete ac_present yes > /dev/null
python3 $H answer sample-complete water_heater_type tank > /dev/null
python3 $H answer sample-complete dryer_present yes > /dev/null
python3 $H answer sample-complete exterior_hose_bibs yes > /dev/null
python3 $H answer sample-complete sump_pump_present yes > /dev/null
python3 $H answer sample-complete closing_date 2026-11-14 > /dev/null
python3 $H equipment sample-complete furnace --make Goodman --model GMVC96 --year 2019 --manual goodman_rs6612023 > /dev/null
python3 $H equipment sample-complete water_heater --make "Bradford White" --model "RG240T6N" --year 2015 --manual bradford_white_io > /dev/null
python3 $H finding sample-complete roof major "Lifted shingles and exposed nail heads at rear slope" --recommendation "Roofer to evaluate and repair" --date 2026-10-20 --source "inspection report p.14" > /dev/null
python3 $H finding sample-complete electrical safety "Open junction box with exposed splices above basement stairs" --recommendation "Licensed electrician to correct" --date 2026-10-20 --source "inspection report p.22" > /dev/null
python3 $H answer sample-complete roof_installed_year 2008 --reason "seller invoice" > /dev/null
python3 $H quote sample-complete FINDING-f-001 450 900 --scope "re-secure lifted shingles and seal exposed nails, rear slope" --exclusions "decking repair if found" --source "ABC Roofing written quote" --date 2026-10-25 > /dev/null
python3 $H quote sample-complete R-HEAT-001 120 220 --scope "annual furnace service incl. CO check" --source "phone quote, two HVAC firms" > /dev/null
python3 $H quote sample-complete R-CHIM-001 150 350 --scope "Level 1 inspection" --source "phone quote, Sweep Co" > /dev/null
python3 $H quote sample-complete R-HEAT-002 15 30 --basis planning_assumption --scope "one pleated filter" --source "typical retail" > /dev/null
python3 $H reserve sample-complete roof 6 9000 16000 --basis planning_assumption --note "owner's planning range; no local price source" > /dev/null
python3 $H reserve sample-complete water_heater 3 1400 2600 --basis planning_assumption > /dev/null
echo "=== CHECKPOINT 4 — CONNECTED REPORTS AND BUDGETS (synthetic sample house; quotes are illustrative, entered by the 'owner') ==="
echo; python3 $H report buy sample-complete
echo; echo "=================================================================="; python3 $H report next sample-complete
echo; echo "=================================================================="; python3 $H report plan90 sample-complete
echo; echo "=================================================================="; python3 $H report calendar sample-complete
echo; echo "=================================================================="; python3 $H report budget sample-complete
echo; echo "=================================================================="; python3 $H report fit sample-complete --hours 2 --dollars 200
echo; echo "=== WHAT CHANGES THE REPORTS: a correction ==="
python3 $H answer sample-complete stage owner --reason "closed 2026-11-14"
python3 $H answer sample-complete wiring_type "rewired" --reason "electrician's letter 2026-11-20"
python3 $H report next sample-complete | head -4
