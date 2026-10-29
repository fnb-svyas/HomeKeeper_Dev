#!/bin/sh
# Regenerates demos/checkpoint6_demo_output.txt (synthetic sample + SYNTHETIC demo providers only).
cd "$(dirname "$0")/.." && sh demos/run_checkpoint5_demo.sh > /dev/null 2>&1
H=homekeeper.py
echo "=== CHECKPOINT 6 — PROVIDER MATCHING (synthetic house; providers shown are SYNTHETIC demo records) ==="
echo; echo "### Inventory"; python3 $H providers list
echo; echo "### Plumber match for the water-heater task"; python3 $H providers match sample-complete R-WH-001
echo; echo "### Electrician match for the safety finding (City-scoped license vs a Mt. Lebanon house)"; python3 $H providers match sample-complete FINDING-f-002
echo; echo "### Chimney match"; python3 $H providers match sample-complete R-CHIM-001
echo; echo "### Thin inventory: roofer"; python3 $H providers match sample-complete R-ROOF-003
echo; echo "### A real (non-sample) house never sees synthetic providers:"; python3 $H --offline build "1 Nowhere Lane, Pittsburgh, PA 15228" --id t-real-demo > /dev/null 2>&1; python3 $H providers match t-real-demo R-ROOF-003 2>&1 | head -6
