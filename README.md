# HomeKeeper — prototype (Checkpoint 9: benchmark and handover)

Know what your house needs next, understand why it matters, prepare for the cost, and keep a record as you get it done.

Pilot: Allegheny County, PA; existing single-family homes with basements built before 1960; buyers under contract with an inspection report, through the first 90 days of ownership.

**Status:** Checkpoint 9 of 9 — prototype complete; expert review not yet performed. Address in → source-tagged house profile; 37 author-reviewed rules (`audit/rule_review.md`); connected reports (before-you-buy, first-90-days, next three, 12-month calendar), three separate budgets built only from recorded quotes/references/planning assumptions, a time-and-budget-constrained view that never hides urgent items; completion/snooze/does-not-apply/reopen with reasons, document references, house history with actual spending, editable contractor job briefs, export and purge; provider inventory from the permitted free sources (importers for ACHD master plumbers and City of Pittsburgh trade licenses, a hand-transcribed PA DEP radon CSV, and a hand-checked directory) with literal, dated credential wording, ranking by suitability → service area → credentials → freshness → distance, and a hiring checklist where inventory is thin (`data/providers/README.md`); reminders as an iCalendar export (`reminders export`) with a stated method — nothing runs in the background, email/push/SMS and weather-triggered reminders are deferred, and the calendar app's own alerts are the notification; a local web app (`python server.py`) over the same record, and a read-only synthetic snapshot for sharing. Benchmark package (`benchmark/`, unfilled), software-check record (`audit/software_checks.md`), implementation guide (`docs/implementation_guide.md`) and limitations/next steps (`audit/limitations_and_next_steps.md`) complete the handover., reminders (CP7), web UI (CP8) and the expert benchmark (CP9) are still to come.

## Windows setup (no installs beyond Python)

1. Install Python 3.9 or newer from python.org if `python --version` in a Command Prompt doesn't show one. Tick "Add python.exe to PATH" in the installer.
2. Unzip this folder somewhere convenient, e.g. `C:\Users\<you>\Documents\homekeeper`.
3. Open Command Prompt there (type `cmd` in the folder's address bar in Explorer).

No packages to install. The whole prototype is Python's standard library.

## First run: check the data endpoints

```
python homekeeper.py doctor
```

Prints one line per endpoint (county geocoder, WPRDC assessments and permits, PA DEP radon, FEMA flood, DEP mine subsidence, county landslide layer, NRCS soils, NCEI climate normals, Census geocoder, NWS) with the HTTP status and the response shape, and writes `audit\doctor_results.json`. Verified 12/12 on the pilot machine on 2026-10-29; a 13th check, `wprdc_comparable_sales`, was added in 0.9.5 for the price benchmark. If `pasda_landslide_prone` ever fails with a certificate error on a new Windows machine, run `python tools\fix_pasda_tls.py` and then `certutil -urlfetch -verify data\certs\pasda_chain_1.pem` (lets Windows install the Sectigo root from Microsoft's trusted-root program; no verification is disabled).

## The app

```
python server.py
```

Then open http://127.0.0.1:8765 in your browser. It binds to this computer only. The first page offers two choices: **Homeowner** (`/owner`) and **Browse Homes** (`/browse` — a prospective buyer's overview of one address: property at a glance, potential major work shown only where specific evidence supports it and labelled documented need / planning consideration / needs assessment, the general upkeep it asks of an owner, and the questions to settle before buying; evidence opens in place; no tasks, reminders or routine items; built only from public and mapped data under its own `browse-` record, so it never reads or changes a homeowner's record; HomeKeeper does not list homes for sale). Each Browse page carries the **HomeKeeper Ownership Score** (0–100): 40% price position (your asking price per sq ft against the median of recent county-classified valid sales of similar homes in the same assessor neighbourhood or municipality — never the tax assessment), 30% ongoing maintenance, 30% major-work exposure. A part without its essential evidence shows as unavailable and the overall score is withheld rather than reweighted; unknown inputs take stated cautious assumptions; evidence completeness is shown separately. Every weight and threshold is in `data/score_config.json` (prototype assumptions, not validated). As a homeowner, enter an address → answer a few questions → one page per house, in this order: who/where and status; **Needs attention** (only when something is a safety finding, overdue, or a deadline within 30 days of closing); **Do next** (three tasks, one Done button each, details in place: why, how, when to call a pro, your equipment, who could do it, the job brief, evidence); postpone / set-aside as one-click choices with undo; one question that would sharpen the plan; **Coming up** (next 60 days and money at a glance); **The house** (the record in plain words, editable in place — the plan updates); **History**. Old addresses redirect. Ctrl+C in the window stops it.

`python server.py --snapshot` writes `demos\snapshot.html`, a read-only page built from the synthetic sample with every form replaced by a label; it is the only thing meant to be published. Real house records never leave this folder unless you export them.

## Offline demonstrations (synthetic data)

```
python homekeeper.py sample complete      # a reasonably complete profile
python homekeeper.py sample missing       # a profile with important gaps
python homekeeper.py sample ambiguous     # two equally scored matches; then:
python homekeeper.py sample ambiguous --choose 1
```

The three sample addresses do not exist; their records are invented to exercise every path. Profiles built from them are marked `SYNTHETIC DEMO DATA`.

## A real address

```
python homekeeper.py build "123 Any St, Pittsburgh, PA 15228"
python homekeeper.py plan 123-any-st-pittsburgh-pa-15228
python homekeeper.py answer 123-any-st-pittsburgh-pa-15228 heating_fuel gas
python homekeeper.py answer 123-any-st-pittsburgh-pa-15228 roof_installed_year 2015 --reason "seller's invoice"
python homekeeper.py show 123-any-st-pittsburgh-pa-15228
python homekeeper.py export 123-any-st-pittsburgh-pa-15228 > my-house.json
```

`equipment` records an identified unit (a replacement retires the old entry and resets age-based rules); `finding` records a documented defect from the inspection report; `responsibility` moves a component to another party (HOA) and off your list. Each prints which recommendations changed.

`report buy|plan90|next|calendar|budget|fit|all` renders the connected reports; `quote` records a cost estimate (user quote, published reference, or labeled planning assumption) for a rule id or component; `reserve` sets a replacement reserve scenario (component, planning years, cost range). Nothing is ever priced without one of those entries.

`done` records a completion (with `--date` for work already done; the recurring clock restarts from that date and the equipment's last-service date updates); `snooze` and `dismiss` keep a task open or mark it does-not-apply with a reason — neither counts as done; `reopen` undoes them; `document` stores a reference to an invoice/manual/warranty/photo/report (the file stays where you keep it); `brief` writes an editable Markdown job brief under `houses\<id>\briefs\`; `history` shows completed work, spending, contractors, equipment and documents; `export` prints the whole record as JSON; `purge --yes` strips private material and keeps the public-record profile.

`answer` records the value with `source: owner`, keeps any disagreeing public-record value as a conflict, and prints which recommendations changed. Answering `unknown` or `none` keeps the field unknown and logs that you said so; it never counts as done.

House records are plain JSON in `houses\`. Network responses are cached in `cache\` (delete the folder to refresh). Nothing is sent anywhere except the public data endpoints queried for the address you enter.

## Benchmark and handover

```
python tools\make_benchmark.py                 # synthetic examples only
python tools\make_benchmark.py --house <id>    # add a real, consented house
```

Writes `benchmark\` with review instructions, empty reviewer columns, and the house records the rows came from. An unfilled benchmark establishes nothing; see `benchmark\README.md` for the denominators and targets. What has actually been checked is listed in `audit\software_checks.md`.

## Tests

```
python -m unittest discover -s tests -v
```

77 software checks run offline (including the web server driven over HTTP) against the synthetic fixtures (evidence model, provenance on correction, ambiguous-match handling, unknown-stays-unknown, rule exclusion/trigger behaviour, every rule cites a registered source).

## Layout

```
homekeeper.py            CLI entry point
server.py                local web app (stdlib http.server; 127.0.0.1 only)
hk/                      package (stdlib only)
  http.py                cached fetch, identifying User-Agent, offline mode
  evidence.py            Field/Profile model: value + source + dates + status + conflicts + history
  geocode.py             county AddressVerification geocoder; Census fallback; ambiguity policy
  records.py             WPRDC assessments (CC0) and City of Pittsburgh permits (CC-BY)
  overlays.py            radon (PA DEP), flood (FEMA), mine subsidence (DEP), landslide (county), soils (NRCS), normals (NCEI)
  municipal.py           hand-curated point-of-sale sewer rules
  builder.py             address -> profile pipeline; owner answers
  buyer.py               Browse Homes overview: glance, evidence-gated major work, upkeep themes, unknowns
  browse.py              Browse Homes pages (dusk theme shared with landing.py)
  score.py               Ownership Score engine (deterministic; config in data/score_config.json)
  score_view.py          score panel: dial, components, drivers, your inputs, method and evidence
  landing.py             landing page
  questions.py           confirmation flow
  rules.py               data-driven rule engine: variants, recurrence, findings, responsibilities, merge, prioritization
  reports.py             before-you-buy, first-90-days, next three, calendar, constrained view
  budget.py              estimates, reserve scenarios, the three budgets (no invented prices)
  actions.py             completions, snooze, does-not-apply, documents, history, purge
  briefs.py              editable contractor job briefs
  providers.py           provider store, importers, matching and hiring checklist
  reminders.py           iCalendar export (RFC 5545 folding, stable UIDs), upcoming list, method statement
  web.py                 HTML rendering for the app (one CSS string; serif record, sans controls; provenance tags)
  report.py              text rendering
  doctor.py              live endpoint checks
  samples.py             SYNTHETIC fixtures
data/
  sources.json           source registry from the Checkpoint 1 audit (64 entries)
  rules.json             37 rules, review_status "author-reviewed" (not expert-validated)
  municipal_dye_tests.json   9 municipalities, compiled 2026-10-29
  codes/assessment_codes.json
audit/                   Checkpoint 1 audit and per-track notes
houses/  cache/          runtime data (git-ignore these)
tests/
```

## Licenses of the data used

Assessments, sales, plumbers and radon tests: CC0 / public domain. City permits and trade licenses: CC-BY City of Pittsburgh. FEMA, NRCS, NCEI, Census, NWS: US government data. County geocoder/GIS and PASDA county layers: free to query, non-commercial disclaimer. **PA DEP mine-subsidence layers: not for commercial use or resale** — the app stores only a yes/no flag and links to DEP's map. Manufacturer manuals and private standards are linked, never copied.
