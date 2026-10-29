#!/bin/sh
# Regenerates demos/checkpoint5_demo_output.txt (synthetic sample; safe to re-run). Builds on the Checkpoint 4 state.
cd "$(dirname "$0")/.." && sh demos/run_checkpoint4_demo.sh > /dev/null 2>&1
H=homekeeper.py
python3 $H answer sample-complete stage owner --reason "closed 2026-11-14" > /dev/null
echo "=== CHECKPOINT 5 — ACTION TRACKING AND HOUSE HISTORY (synthetic sample; dates/costs illustrative) ==="
echo; echo "### Next three before any action"; python3 $H report next sample-complete | grep -E "^[0-9]\."
echo; echo "### 1. Done: annual furnace service (recurring) — the clock restarts from the actual date"
python3 $H done sample-complete R-HEAT-001 --date 2026-10-20 --cost 165 --contractor "Keystone HVAC" --notes "CO reading 3 ppm; blower cleaned"
echo; echo "### 2. Already completed: the inspection's radon test, with its real date"
python3 $H done sample-complete R-RADON-001 --date 2026-09-30 --notes "inspection radon test 1.9 pCi/L (lab report filed)"
python3 $H answer sample-complete radon_result_date 2026-09-30 > /dev/null; python3 $H answer sample-complete radon_result_pci_l 1.9 > /dev/null
echo; echo "### 3. Snooze (stays open; never counts as done)"; python3 $H snooze sample-complete R-GUTTER-001 2026-11-20 --reason "leaves not down yet"
echo; echo "### 4. Does not apply (reason required; not done)"; python3 $H dismiss sample-complete R-DRYER-001 "no dryer; use laundromat"
echo; echo "### 5. Correct the underlying house information instead of dismissing"; python3 $H answer sample-complete exterior_hose_bibs no --reason "none; previous owner capped them"
echo; echo "### 6. Responsibility change"; python3 $H responsibility sample-complete sewer_lateral "shared with neighbor (party agreement)" --reason "recorded easement"
echo; echo "### 7. Job brief for the safety finding (editable Markdown)"; python3 $H brief sample-complete FINDING-f-002 --show
echo; echo "### 8. Resolve the roof finding with the invoice"
python3 $H document sample-complete invoice "ABC Roofing invoice 2026-11-21" "House/roof-invoice-2026.pdf" --component roof --task FINDING-f-001
python3 $H done sample-complete FINDING-f-001 --date 2026-11-21 --cost 650 --contractor "ABC Roofing" --notes "re-secured shingles, sealed nails" --doc d-001
echo; echo "### 9. Replacement recorded with its manual and warranty"
python3 $H equipment sample-complete sump_pump --make Zoeller --model M53 --year 2026 --manual zoeller_fm2676 --note "installed 2026-11-28 by Keystone Plumbing"
python3 $H document sample-complete warranty "Zoeller 3-year warranty (FM2676)" "https://zoellerpumps.com/wp-content/uploads/sites/3/2026/07/fm2676-3-Year-Warranty-Installation-Instructions.pdf" --component sump_pump
echo; echo "### Next three after these actions"; python3 $H report next sample-complete | grep -E "^[0-9]\."
echo; echo "### Plan groups"; python3 $H plan sample-complete | grep -E "^(SNOOZED|MARKED|DONE|SOMEONE)|^  R-(GUTTER|DRYER|SEWER-00|RADON-001|HEAT-001)" 
echo; echo "### Budgets reflect actual spending and the resolved finding"; python3 $H report budget sample-complete | sed -n '/KNOWN REPAIRS/,/FUTURE/p'
echo; echo "### House history"; python3 $H history sample-complete
echo; echo "### Export (first lines) and purge are available: 'export <id>' / 'purge <id> --yes'"; python3 $H export sample-complete | head -5
