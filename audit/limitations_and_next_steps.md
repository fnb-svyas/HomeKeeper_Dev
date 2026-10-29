# Known limitations and next steps — HomeKeeper prototype (end of Checkpoint 9)

## Known limitations

**Evidence and validation**
- No recommendation has been independently reviewed. The benchmark package exists and is empty. The 95% / 90% / zero-critical-error targets are proposals.
- Rules are "author-reviewed": the author checked each cited source states the recommendation. That is not inspector judgment.
- Three intervals are planning assumptions with no primary source (gutter cleaning, dryer duct, sump test without a known model); labelled as such.
- Equipment refinement covers 6 audited manuals; the brief's "≥10 identified models" check cannot run until more are audited.

**Data**
- Permit history exists only for City of Pittsburgh parcels (June 2019+). Outside the City, the record says so.
- Equipment age is not in any public record; it comes only from the owner, labels or documents.
- Municipal point-of-sale sewer rules: 9 of ~130 municipalities compiled; the rest route to a verification task.
- The ACHD plumber list is frozen (2026-07-29) and undercounts; the City list is weekly but City-scoped; PA has no state license for electricians, HVAC or roofers — only HICPA registration, which is a manual check.
- Landslide layer covers the City extent only; "not mapped" is shown, not "not prone".
- DEP mining layers are non-commercial: flag-and-link only; legal review needed before any commercial use.
- No free, licensable local cost source exists. Budgets price only user quotes, published references and labelled planning assumptions.
- Public-record fields are a monthly snapshot of assessor data recorded for valuation; condition/grade are valuation categories.

**Product**
- Reports and provider pages render as styled text documents in the app, not native HTML tables.
- Reminders are a calendar file; no email/push/SMS; no weather triggers; nothing runs in the background.
- Document extraction (inspection PDFs, equipment labels) is not implemented; entry is manual by design for the pilot.
- The constrained view parses effort from rule text; "1 visit" and "depends on scope" are treated as unknown time.
- Single-user, local-only; no accounts, no sync, no concurrent editing.
- The hosted snapshot is read-only and synthetic; it cannot demonstrate the correction loop live.

## Next steps, ordered by unresolved user value and evidence gaps

1. **Fill the benchmark.** Recruit 20 consented pilot households (inspection report in hand) and one or two licensed inspectors; assign dev/holdout; review; fix rules only from dev findings; report the rates with the split rate. This is the gating item — nothing else changes the product's credibility as much.
2. **Run the five-person task test** on the local app with the synthetic house, then the 30-day pilot with real households, tracking completed actions and categorised dismissals.
3. **Audit four or more additional equipment manuals** (Lennox/Trane/Rheem furnaces, Rheem/Bradford White residential atmospheric water heater, a Wayne sump, a backwater valve) so the equipment-rule check can run at ≥10 models.
4. **Compile more municipal point-of-sale rules** (South Hills and eastern suburbs first, by pilot household location) with the same "verify with municipality" stamp.
5. **Document intake without an LLM**: a form that walks the inspection report section by section (roof, exterior, basement, heating, plumbing, electrical) into findings, mirroring the InterNACHI SOP scope; later, optional label-photo capture with mandatory confirmation.
6. **Provider inventory**: hand-check a small set of HVAC, roofing and chimney providers in two or three municipalities (HICPA number + date), and transcribe the Allegheny rows of the DEP radon PDF — the three trades the pilot stock needs most that no dataset covers.
7. **Native HTML for reports and providers** in the app, once the content has survived expert review (no point polishing text that may change).
8. **Reminder delivery** only if the pilot shows the .ics method is not used: a scheduled local task or a hosted job would be the first process that runs unattended, and should be a deliberate decision.
9. **Legal review** of the DEP non-commercial layers and the county GIS disclaimer before any commercial use; a Right-to-Know request to the PA AG for a bulk HICPA registrant list if the project continues.
10. **Broaden the stock** (post-1960, slab, condos/HOA) only after the pre-1960 basement rules hold up in review; each new system needs its own sourced rules, not a copy.
