#!/bin/sh
# Regenerates demos/checkpoint7_demo_output.txt (synthetic sample; safe to re-run). Builds on the Checkpoint 5 state.
cd "$(dirname "$0")/.." && sh demos/run_checkpoint5_demo.sh > /dev/null 2>&1
H=homekeeper.py
echo "=== CHECKPOINT 7 — REMINDERS (synthetic sample house) ==="
echo; python3 $H reminders method
echo; echo "### Upcoming 90 days (after the Checkpoint 5 actions: furnace service done 10-20, gutters snoozed to 11-20, dryer dismissed, roof finding resolved)"
python3 $H reminders list sample-complete --days 90
echo; echo "### Export"; python3 $H reminders export sample-complete | head -1
echo; echo "### First event in the .ics (CRLF, folded to 75 octets, stable UID, all-day, 1-day-before alarm)"
python3 - <<'PY'
import pathlib
s=pathlib.Path('houses/sample-complete/reminders.ics').read_bytes().decode('utf-8')
blk=s.split('BEGIN:VEVENT')[1].split('END:VEVENT')[0]
print('BEGIN:VEVENT'+blk.replace('\r\n','\n')+'END:VEVENT')
PY
echo; echo "### Recording a completion and re-exporting moves the series (same UIDs for unchanged events)"
python3 $H done sample-complete R-ALARM-001 --date 2026-10-29 --notes "all 5 alarms tested; dates 2019-2022"
python3 $H reminders list sample-complete --days 45 | grep -A1 "Test smoke" | head -4
python3 $H reminders export sample-complete | head -1
