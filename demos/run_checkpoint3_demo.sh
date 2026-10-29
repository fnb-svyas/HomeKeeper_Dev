#!/bin/sh
# Regenerates demos/checkpoint3_demo_output.txt from the synthetic sample (safe to re-run).
cd "$(dirname "$0")/.." && rm -f houses/sample-complete.json
H=homekeeper.py
echo "=== CHECKPOINT 3 DEMONSTRATIONS (synthetic sample house: 1928 brick colonial, Mt. Lebanon, full basement, 1 fireplace) ==="
python3 $H sample complete > /dev/null
echo; echo "### 1. A rule that applies (from public record alone)"; python3 $H plan sample-complete | grep -A9 "R-CHIM-001  Annual" | head -10
echo; echo "### 2. A rule excluded by confirmed information"
python3 $H answer sample-complete heating_fuel "heat pump" --reason "heat pump installed, no combustion appliances"
python3 $H answer sample-complete chimney_in_use no --reason "fireplace sealed"
python3 $H plan sample-complete | grep -A2 "EXCLUDED BY CONFIRMED" | head -8
echo; echo "### 3. A rule requiring verification"
python3 $H plan sample-complete | grep -A6 "R-SUMP-001  Test the sump pump" | head -7
echo; echo "### 4. Generic recommendation refined by equipment-specific instructions"
python3 $H answer sample-complete heating_type "forced air"
echo "--- before identifying the furnace:"; python3 $H plan sample-complete | grep -A3 "R-HEAT-002  Check the furnace" | head -4
python3 $H equipment sample-complete furnace --make Goodman --model GMVC96 --year 2019 --manual goodman_rs6612023
echo "--- after:"; python3 $H plan sample-complete | grep -A5 "R-HEAT-002  Check the furnace" | head -6
echo; echo "### 5. A task changed by a recent replacement"
python3 $H answer sample-complete water_heater_type tank
python3 $H answer sample-complete water_heater_installed_year 2012 --reason "label date"
echo "--- 2012 heater:"; python3 $H plan sample-complete | grep -A1 "R-WH-002  Plan a water-heater" | head -2
python3 $H equipment sample-complete water_heater --make "A. O. Smith" --model "GCR-50" --year 2026 --manual aosmith_100398943 --note "replaced 2026-10-20, invoice on file"
echo "--- after replacement:"; python3 $H plan sample-complete | grep -A4 "R-WH-001  Water heater" | head -5
python3 $H plan sample-complete | grep -A2 "R-WH-003  Register" | head -3
python3 $H show sample-complete | grep -A2 "^  water_heater_installed_year"
echo; echo "### 6. An HOA responsibility that removes work from the homeowner's action list"
python3 $H finding sample-complete roof major "Lifted shingles and exposed nail heads at rear slope" --recommendation "Roofer to evaluate and repair" --date 2026-10-20 --source "inspection report p.14"
echo "--- documented finding ranks first:"; python3 $H plan sample-complete | grep -A3 "NEXT 3" | head -4
python3 $H responsibility sample-complete roof HOA --reason "condo association owns roof and gutters per declaration 4.2"
python3 $H responsibility sample-complete gutters_downspouts HOA --reason "same"
echo "--- after:"; python3 $H plan sample-complete | grep -A3 "SOMEONE ELSE" | head -5
python3 $H plan sample-complete | grep -A3 "NEXT 3" | head -4
echo; echo "### Final house record"; python3 $H show sample-complete | sed -n '/EQUIPMENT/,/REGIONAL/p'
echo; echo "### Full plan"; python3 $H plan sample-complete
