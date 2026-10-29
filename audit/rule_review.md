# Rule base review — Checkpoint 3

Rule file: `data/rules.json` (schema 0.2). 37 rules. Reviewed 2026-10-29 by the author against the sources audited in Checkpoint 1. **This is author review, not expert validation.** The Checkpoint 9 benchmark is where a licensed inspector marks each recommendation correct / incorrect / unsupported / missing a qualification.

## What "author-reviewed" means here

For every rule the author confirmed, during the Checkpoint 1 audit, that the cited document actually states the recommendation (interval, threshold, or action) — not merely that a URL exists. Where no primary source states an interval, the rule says so in its recurrence (`"basis": "planning_assumption"`) and in its action text. Where free sources disagree (water heater sediment/anode intervals), the rule presents the range and names the source for each bound; the installed unit's manual overrides via `variants`.

## Coverage by pilot system

| System (pre-1960, basement, Allegheny County) | Rules | Source class | Gaps |
|---|---|---|---|
| Smoke/CO alarms, GFCI | R-ALARM-001/002, R-GFCI-001 | CPSC/USFA (public domain) | CO alarm replacement age is "per label" (CPSC gives no number) |
| Electrical (knob-and-tube, ungrounded) | R-ELEC-001 | CPSC Pub 099 + InterNACHI SOP scope | No free source gives remediation guidance; rule is verification + referral |
| Heating (gas/oil furnace or boiler) | R-HEAT-001/002/003 | CPSC NSN-9, DOE Energy Saver; variants Goodman, Carrier | Carrier variant is from a 2001 manual; current Carrier manuals are on a bot-blocked portal |
| Central AC | R-AC-001 | DOE Energy Saver | No manufacturer variants yet |
| Water heater (tank) | R-WH-001/002/003 | DOE; variants Bradford White, A. O. Smith; InterNACHI/NAHB ages; Goodman/Carrier warranty terms | Bradford White variant uses a direct-vent manual; residential atmospheric manual still to locate. Tankless: excluded, no rules yet |
| Chimney | R-CHIM-001 | CSIA (NFPA 211 via CSIA), CPSC | NFPA 211 itself is paid; never cited directly |
| Roof | R-ROOF-001/002/003 | InterNACHI SOP + chart, NAHB 2007, NRCA via Professional Roofing | Slate/metal roofs: only excluded from asphalt planning; no slate-specific rule (no free primary source found) |
| Gutters / grading / basement moisture | R-GUTTER-001, R-GRADE-001, R-BSMT-001 | ISU Extension Pm-1560, EPA Mold Guide | Gutter-cleaning cadence is a planning assumption; EPA says only "regularly" |
| Sump pump | R-SUMP-001/002 | Zoeller FM2676, Liberty 7035000 variants; InterNACHI age | Backwater valve: no manual located; no rule |
| Radon | R-RADON-001/002/003 | EPA Citizen's Guide, Buyer's/Seller's Guide, Consumer's Guide to Radon Reduction | — |
| Lead paint | R-LEAD-001 | EPA Section 1018 page | CFR citation to add after manual verification |
| Dryer | R-DRYER-001 | CPSC Pub 5022 | Cleaning interval is a planning assumption (CPSC: "periodically") |
| Freeze protection | R-FREEZE-001 | NCEI normals for the date | The practice itself (drain hose bibs) has no primary source; labelled |
| Flood / mine subsidence / landslide / soil | R-FLOOD-001, R-MSI-001, R-SLOPE-001, R-SOIL-001 | FEMA, DEP MSI, PASDA county layer, NRCS SDA | All are regional exposure → verification tasks, never diagnoses |
| Sewer lateral / dye test | R-SEWER-001/002 | 9 municipal pages/codes; ALCOSAN | Only 9 of ~130 municipalities compiled; unknown municipality → verification |
| Plumbing materials | R-PLUMB-001 | InterNACHI chart; PWSA lead-line program | Lead in supply piping escalates to health; no free remediation-cost source |
| Termite / WDI | R-WDI-001 | Shaler Twp UCC ordinance (IRC R301.2 value); PA disclosure form item 5 | — |
| Transaction (disclosure, permits) | R-DISC-001, R-PERMIT-001 | 68 Pa.C.S. §7304; PA L&I UCC | 34 Pa. Code §403.21 text to verify manually (site blocks bots) |
| Envelope (optional) | R-AIR-001 | DOE Energy Saver | Deliberately last; optional |

**Not covered (and why):** tankless water heaters (no manual audited); heat-pump-specific maintenance (DOE AC rule applies partially); well/septic (not in pilot stock); asbestos (EPA guidance not yet audited); window/door replacement (optional, no safety driver); masonry repointing (no free primary interval source); slate roof care (no free primary source); driveway/walk (optional).

## How the engine resolves the questions in section 5 of the brief

- **Conflicting sources:** a rule cites one primary source. Where free sources disagree on an interval, the rule text states both bounds with their sources (R-WH-001). When installed equipment has a reviewed `variants` entry, the manufacturer interval replaces the generic one and both sources are shown (`refined_by`).
- **Equipment-specific precedence:** `variants` keyed by the manual's source id. Manufacturer instructions override DOE/InterNACHI guidance; the reverse never happens. If a manual is on file but has no reviewed variant, the task says so and shows generic guidance.
- **General vs manufacturer requirement:** the task's `sources` list and `refined_by` line make the origin visible; warranty-linked requirements are their own rule (R-WH-003) with an event trigger.
- **Duplicate tasks:** `merge_key` (e.g. `annual-heating-service`) merges live tasks; highest severity wins, sources are unioned, both rule ids remain in the reason.
- **New findings / replacements:** findings become `FINDING-*` tasks with professional-finding evidence and rank above preventive tasks; `add_equipment` retires the previous unit (status `replaced`, kept in history), the profile's `<component>_installed_year` is corrected with the equipment record as its source, age-based rules recompute, and a current-year install triggers the registration deadline.
- **Rule updates vs history:** rules carry `version`; task instances (Checkpoint 5) will store the rule id and version they were generated from, so a rule change affects future tasks without rewriting completed ones.
- **Recurrence:** `one_time`, `fixed_date` (next occurrence), `seasonal_window` (in season / next window), `interval_since_completion` (no record → "due now"; else next due or overdue), `equipment_interval` (same, keyed to the equipment's last service), `event`. Month arithmetic is leap-year and short-month safe (tested). Snoozes, local time and duplicate reminders are Checkpoint 5/7 items.
- **Unknown handling:** per rule `when_unknown` = ask / verify / apply / skip; `silent_when_unknown` keeps event-driven rules out of the "data gap" list.

## Prioritization (explainable, no score)

Tiers, in order: documented safety findings → documented major findings (active, strong evidence) → safety rules → other findings → health → deadlines → damage prevention → budget planning → comfort → info. Within a tier: status (applies before verification before needs-info), evidence strength (professional/manufacturer > owner > public record > regional > inference > unknown), then how soon a seasonal window closes. The `priority:` line on each task prints these factors. Reasonable people will disagree about where deadlines sit relative to monthly safety tests; this is the first thing to put in front of the expert reviewer.

## Rule count

37 total. By category: preventive 15, verification 12, replacement_planning 4, deadline 3, documented_defect 1, info 1, optional 1. The brief's "60" was not a target; each rule here earned its place by having a source that supports it and a pilot-stock reason to exist.
