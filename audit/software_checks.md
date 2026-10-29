# Software checks actually run — HomeKeeper prototype

These are checks that were executed, with where and when. They are software checks only; none is expert validation,
usability evidence, or evidence of customer value (see `benchmark/README.md` for what those would require).

| Check | Where | When | Result |
|---|---|---|---|
| Unit/integration suite, `python -W error -m unittest discover -s tests` (47 tests: evidence model, provenance on correction, ambiguous match, unknown handling, rule schema/sources, exclusion-beats-trigger, equipment refinement, replacement reset, HOA removal, recurrence/leap-year math, merge, budgets never invent prices, overlap flag, constrained view never hides urgent items, report consistency, completion/snooze/dismiss semantics, finding resolution, briefs contain no diagnosis, purge, provider ranking/wording/relevance, ICS validity and UID stability, reminder behaviour, web routes and actions over HTTP) | pilot machine (Windows, Python 3.10.12) and development sandbox (Python 3.13) | 2026-10-29 | OK on both; warnings treated as errors |
| Live endpoint check, `python homekeeper.py doctor` (12 endpoints) | pilot machine | 2026-10-29 13:47 UTC | 12/12 HTTP 200 with documented response shapes (`audit/doctor_results.json`) |
| PASDA TLS chain fix (`tools/fix_pasda_tls.py` + `certutil -urlfetch -verify`) | pilot machine | 2026-10-29 | chain verifies; no verification disabled |
| Provider importers against live WPRDC (`providers discover/import achd/import city`) | pilot machine | 2026-10-29 | ACHD fields verified and importer corrected; 608 ACHD rows, 1,569 City electrical licenses; `expiration_date` and `license_state` present |
| ICS structural validation (CRLF, ≤75-octet lines, unique stable UIDs, required properties) | sandbox + test suite | 2026-10-29 | pass |
| Web pages at 390 px width: no horizontal overflow on 8 pages (Playwright) | sandbox | 2026-10-29 | scrollWidth 390 on all |
| Python 3.10 compatibility scan for f-string backslash expressions | sandbox | 2026-10-29 | none remaining (one found and fixed after a failure on the pilot machine) |
| Checkpoint demos regenerated from scripts (`demos/run_checkpoint*_demo.sh`) | sandbox | 2026-10-29 | outputs in `demos/` |

## Not run (and therefore not claimed)
- Expert review of recommendations (benchmark is unfilled).
- Comparison of generated schedules with current manuals for ≥10 identified models: the package covers the 6 manuals audited (Goodman, Carrier, Bradford White, A. O. Smith, Zoeller, Liberty); 4+ more manuals must be audited and added to `data/sources.json` and the rules' `variants` first.
- Provider-match review (template is empty).
- Five-person usability test; 30-day household pilot.
- Any measurement of money saved or damage avoided (the product does not claim either).
