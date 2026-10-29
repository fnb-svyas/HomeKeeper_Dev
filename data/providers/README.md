# Provider store

`providers.json` ships with **synthetic demo entries only** (flagged `synthetic: true`; shown only for sample houses). Nothing here is a real provider until you import or add one.

Permitted free sources (from the Checkpoint 1 audit) and how to load them, on your machine:

```
python homekeeper.py providers discover            # prints the field names WPRDC returns (the audit could not verify them)
python homekeeper.py providers import achd         # Allegheny County registered master plumbers (CC0; list frozen 2026-07-29)
python homekeeper.py providers import city         # City of Pittsburgh trade licenses, electrical (CC0, weekly; City scope only)
python homekeeper.py providers import radon data/providers/radon_allegheny.csv --date 2026-10-01
                                                   # after hand-transcribing the Allegheny rows of PA DEP's monthly PDF into the CSV template
python homekeeper.py providers add "Name" plumber --phone ... --area "Mt. Lebanon" --area "Dormont"
python homekeeper.py providers verify p-0007 hicpa --identifier PA123456 --status active --date 2026-11-02
python homekeeper.py providers geocode             # county geocoder for distance; cached
python homekeeper.py providers match <house-id> R-HEAT-001
```

Every credential records type, identifier, status, date, source and who checked it, and is rendered only in the literal wording in `hk/providers.py` (never "licensed", "insured" or "vetted" as generic badges). HICPA registration is a manual check by design: the AG search has no API and its terms grant no automated access.
