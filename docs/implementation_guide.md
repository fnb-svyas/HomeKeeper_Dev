# HomeKeeper — implementation guide

For whoever picks this up next. Short by design; the code is small and the audit documents carry the reasoning.

## 1. What it is
A zero-cost, standard-library Python prototype for the Allegheny County pre-1960 single-family pilot. One house record
(JSON) per house; everything else — plan, reports, budgets, reminders, provider matches — is a view computed from that
record plus a declarative rule base. Nothing runs in the background. No API keys. No LLM.

## 2. Layout and data flow
```
address ─► hk/geocode (county AddressVerification; Census fallback) ─► candidates, ambiguity policy
        ─► hk/records   (WPRDC assessments by PARID; City permits)   ─► Fields (public_record, unverified)
        ─► hk/overlays  (DEP radon by ZIP, FEMA NFHL, DEP MSI, PASDA landslide, NRCS SDA, NCEI normals) ─► regional_exposure Fields
        ─► hk/municipal (hand-curated dye-test table)
        ─► Profile (hk/evidence) saved to houses/<id>.json
Profile + data/rules.json ─► hk/rules.evaluate ─► Task list ─► prioritize (explainable tiers)
Task list ─► hk/reports (buy, 90-day, next three, calendar, constrained) ─► hk/budget (three budgets) ─► hk/reminders (.ics)
Owner actions (hk/actions): answers, equipment, findings, responsibilities, done/snooze/dismiss, documents ─► Profile
hk/providers: store + importers + match; hk/briefs: job briefs; hk/web + server.py: the app; homekeeper.py: the CLI
```

## 3. The evidence model (hk/evidence.py)
`Field` = value, units, source_id (from `data/sources.json`), source_ref, observed_date, retrieved_date, evidence_type,
verification_status, limitations, conflicts[], history[]. `Profile.correct()` never erases: the old field goes to
history and, if it was a public record that disagrees, to conflicts. `unknown` is a real state (value None); rules decide
what unknown means via `when_unknown`.

## 4. Rules (data/rules.json, hk/rules.py)
Each rule: id, version, component, task_category, trigger[], exclusions[], required_fields[], when_unknown
(ask|verify|apply|skip), action, why, recurrence, severity, priority_rationale, diy_pro, completion_criteria, cost,
source_id + source_ref, review_status. Optional: equipment_component + variants{manual_source_id → months/action/source_ref},
merge_key, verification_task, silent_when_unknown, responsibility_sensitive.
Evaluation order: responsibility → exclusions → required fields → triggers → equipment refinement → due date.
Findings become tasks outside the rule base. Snoozes/dismissals/one-time completions overlay statuses last.

Adding a rule: write it with a source already in `data/sources.json` (add the source first via
`audit/build_sources_json.py`), run the tests (`test_rule_schema_and_sources` enforces this), and log it in
`audit/rule_review.md`. Bump `version` on any change that alters what a task says; completed tasks keep the version they
satisfied.

## 5. Recurrence
one_time · fixed_date (MM-DD) · seasonal_window · interval_since_completion (months; optional window; reset_on_install) ·
equipment_interval · event. Due labels come from the latest completion for that rule, else the equipment's last service date,
else "due now — no completion on record". Month arithmetic is leap-year safe (`_add_months`). Dates are local calendar days;
no time-of-day anywhere.

## 6. Sources and licensing (data/sources.json, audit/)
64 audited entries with decision, verification state, license class and limitations. `permitted_use` governs what the app
may store: `redistribute` (CC0/public domain), `attribute`, `paraphrase_attribute`, `link_only`, `paid`. The DEP mining
layers are non-commercial: the app stores a yes/no flag and links out. Manufacturer manuals are linked, never mirrored.

## 7. Providers (hk/providers.py, data/providers/)
Records separate existence / categories / service_area / credentials. Credentials render only through
`CREDENTIAL_WORDING`. Importers: ACHD plumbers (CC0, frozen 2026-07-29; duplicates per person merged), City trade licenses
(CC0, weekly, City scope), DEP radon CSV (hand-transcribed). HICPA and CSIA are manual (`providers verify`).
`providers.json` is never overwritten by a sync; synthetic entries are shown only for sample houses.

## 8. Running
Windows: `python server.py` → http://127.0.0.1:8765; `python homekeeper.py …` for the CLI; `python -W error -m unittest
discover -s tests` for the checks; `python homekeeper.py doctor` for endpoints; `python tools\make_benchmark.py` for the
review package; `python server.py --snapshot` for the shareable synthetic page.
If PASDA fails TLS on a new machine: `python tools\fix_pasda_tls.py` then `certutil -urlfetch -verify data\certs\pasda_chain_1.pem`.

## 9. First likely paid service
Google Places API (New): would add business existence/hours/reviews near the address, but requires billing, forbids
storing provider names/addresses, and yields weaker evidence than the public registries. Unnecessary for the pilot.
Second candidate: a transactional email service for reminder delivery — unnecessary while the .ics method is acceptable.

## 10. Costs, separated
Software: $0. Development time so far: one working session. Expert review: a licensed inspector's time for ~20 houses
(not free, not done). Hosting: the local app needs none; the synthetic snapshot is a static page. Later operating costs:
none until delivery/hosting/paid data are added.
