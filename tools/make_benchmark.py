r"""Build the expert-review benchmark package (Checkpoint 9).

Run:  python tools\make_benchmark.py            # synthetic examples only (safe to share)
      python tools\make_benchmark.py --house <id> # add a real, CONSENTED house record to the package

Writes benchmark/:
  README.md                    review instructions, denominators, error categories, disagreement handling
  recommendations_review.csv   one row per presented recommendation, with EMPTY reviewer columns
  omissions_review.csv         empty table for important actions the reviewer thinks are missing
  equipment_rule_check.csv     generated schedule vs manufacturer manual, per identified unit (empty reviewer columns)
  provider_match_review.csv    copied from audit/ (empty)
  usability_tasks.md           the five-person task-test script and the 30-day pilot log template
  houses/<id>.json             the house records the rows were generated from (synthetic ones say so)
  manifest.json                what was generated, when, from which rule and source versions

An unfilled benchmark establishes nothing. The headline numbers in the brief (95% correct, 90% coverage,
no critical safety errors) are targets for a filled benchmark reviewed by a qualified inspector, not results.
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hk import HOUSES, VERSION, builder, http, rules, samples  # noqa: E402
from hk.evidence import Profile  # noqa: E402

OUT = ROOT / "benchmark"
REC_COLS = ["house_id", "synthetic", "set", "task_id", "rule_version", "status", "severity", "category", "title", "action",
            "why", "evidence_summary", "source", "reviewer_verdict(correct_applicable|incorrect|unsupported|missing_qualification)",
            "reviewer_severity_agree(Y/N)", "critical_safety_error(Y/N)", "reviewer_note", "reviewer", "review_date"]
OMIT_COLS = ["house_id", "set", "component", "important_action_missing", "why_it_matters", "in_scope(Y/N)", "reviewer", "review_date"]
EQ_COLS = ["house_id", "equipment_id", "component", "make", "model", "manual_source_id", "rule_id", "generated_interval_months",
           "generated_action", "manual_states(reviewer fills)", "agrees(Y/N/ambiguous)", "reviewer_note", "reviewer", "review_date"]


def synthetic_houses() -> list[Profile]:
    """Three synthetic houses with different ages/systems, built offline, labelled synthetic."""
    out = []
    for name in ("complete", "missing"):
        http.clear_fixtures(); http.set_offline(True)
        addr = samples.install(name)
        p = builder.build(addr, house_id=f"bench-syn-{name}", mode="offline-sample", synthetic=True)
        out.append(p)
    # variant: the complete house as an owner with answers and findings (exercises more rules)
    http.clear_fixtures(); http.set_offline(True)
    p = builder.build(samples.install("complete"), house_id="bench-syn-complete-owner", mode="offline-sample", synthetic=True)
    for k, v in {"heating_fuel": "gas", "heating_type": "forced air", "ac_present": True, "water_heater_type": "tank",
                 "dryer_present": True, "exterior_hose_bibs": True, "sump_pump_present": True, "stage": "owner",
                 "closing_date": "2026-11-14", "roof_installed_year": 2008, "wiring_type": "knob-and-tube"}.items():
        builder.apply_answer(p, k, v)
    p.add_equipment("furnace", make="Goodman", model="GMVC96", installed_year=2019, manual_source_id="goodman_rs6612023")
    p.add_equipment("water_heater", make="Bradford White", model="RG240T6N", installed_year=2015, manual_source_id="bradford_white_io")
    p.add_equipment("sump_pump", make="Zoeller", model="M53", installed_year=2022, manual_source_id="zoeller_fm2676")
    p.add_finding("roof", "major", "Lifted shingles and exposed nail heads at rear slope", source_doc="inspection report p.14", observed_date="2026-10-20")
    p.add_finding("electrical", "safety", "Open junction box with exposed splices above basement stairs", source_doc="inspection report p.22", observed_date="2026-10-20")
    p.save()
    out.append(p)
    http.set_offline(False); http.clear_fixtures()
    return out


def rows_for(p: Profile, set_name: str) -> tuple[list[dict], list[dict]]:
    tasks = rules.evaluate(p)
    rec, eq = [], []
    versions = {r["id"]: r["version"] for r in rules.load_rules()}
    for t in tasks:
        if t.status not in ("applies", "verification", "needs_info", "finding"):
            continue
        ev = "; ".join(f"{x['field']}={x['value'] if x['value'] is not None else 'unknown'} ({x['evidence_type']})" for x in t.evidence)
        rec.append({"house_id": p.house_id, "synthetic": p.synthetic, "set": set_name, "task_id": t.rule_id,
                    "rule_version": versions.get(t.rule_id, ""), "status": t.status, "severity": t.severity, "category": t.category,
                    "title": t.title, "action": t.action, "why": t.why, "evidence_summary": ev,
                    "source": " | ".join(f"{s['source_id']}: {s['ref']}" for s in t.sources)})
    for e_ in p.equipment:
        if e_.get("status") != "installed":
            continue
        for t in tasks:
            if t.status == "applies" and t.refined_by and e_["component"] in t.refined_by.lower().replace(" ", "_") or \
               (t.status == "applies" and any(s["source_id"] == e_.get("manual_source_id") for s in t.sources)):
                eq.append({"house_id": p.house_id, "equipment_id": e_["id"], "component": e_["component"], "make": e_.get("make", ""),
                           "model": e_.get("model", ""), "manual_source_id": e_.get("manual_source_id", ""), "rule_id": t.rule_id,
                           "generated_interval_months": (t.recurrence or {}).get("months", ""), "generated_action": t.action})
    return rec, eq


def write_csv(path: pathlib.Path, cols: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


README = """# HomeKeeper expert-review benchmark

**Status: UNFILLED.** Every reviewer column in these files is empty. An unfilled benchmark establishes nothing about
accuracy; the targets below are proposed pilot targets, not results and not industry benchmarks.

## What is in this package
- `recommendations_review.csv` — one row per recommendation HomeKeeper presented for each house (statuses applies,
  verification, needs-info, and documented findings). Columns up to `source` are generated; the rest are for the reviewer.
- `omissions_review.csv` — for important actions, within the product's scope, that HomeKeeper did NOT present.
- `equipment_rule_check.csv` — each generated interval/action for an identified unit, to be compared with the unit's
  current manual (linked by `manual_source_id` in `data/sources.json`).
- `provider_match_review.csv` — task→provider matches to check for suitability and service-area evidence, credential
  wording against the cited source, and that unknowns stay unknown.
- `usability_tasks.md` — the five-person task test and the 30-day household pilot log.
- `houses/` — the house records the rows came from. Files whose name starts with `bench-syn-` are SYNTHETIC: invented
  addresses and invented facts, used only to exercise the rules. Real houses appear here only with the owner's consent and
  are never to be published.

## Who reviews
A home inspector familiar with Allegheny County housing stock, licensed where required (Pennsylvania licenses home inspectors
under the Home Inspection Law, 68 Pa.C.S. Ch. 75). Two reviewers are preferred so disagreement can be measured.

## How to review a recommendation row
Read the house record (`houses/<id>.json`) and any attached inspection report, then mark `reviewer_verdict`:
- `correct_applicable` — the recommendation is right for this house as evidenced, with adequate qualification.
- `incorrect` — wrong for this house (e.g., task contradicts the record or the cited source).
- `unsupported` — the cited source does not support the recommendation as stated.
- `missing_qualification` — right in substance but needs a caveat the text lacks.
Mark `critical_safety_error` Y only when following the recommendation as written could plausibly cause injury or when a
safety hazard evident in the record is contradicted. Any Y blocks release.

## Denominators and targets (proposed)
- Correct-and-applicable rate = correct_applicable ÷ all presented rows (needs-info and verification rows count as presented).
  Target ≥ 95%.
- Coverage = (expert-identified important in-scope actions that appear in the rows) ÷ (all expert-identified important
  in-scope actions, from `omissions_review.csv` plus rows marked correct). Target ≥ 90%.
- Every high-priority recommendation (severity safety/health/deadline) must be `correct_applicable` or a verification task
  that explicitly requests the missing evidence.
- Zero critical safety errors in the reviewed sample.
- Equipment: every `equipment_rule_check.csv` row must be `Y` or `ambiguous` with the ambiguity written in the note.
- Providers: ≥ 90% of matches with suitability and service-area evidence; every credential string matches its source;
  unknowns displayed as unknown; registration never presented as competence.

## Disagreement
Two reviewers who disagree on a verdict discuss once; if still split, the stricter verdict stands and the row is flagged
`split` in `reviewer_note`. Report the split rate alongside the rates above.

## Development vs holdout
`set` = `dev` rows may be used to fix rules; `holdout` rows are reviewed only after rule changes stop. The synthetic houses
are all `dev`. Assign real consented houses alternately to `dev` and `holdout` as they are added.

## What this benchmark cannot show
Reviewing a small sample does not prove universal safety or accuracy. It measures this rule base against these houses on
this date, with these reviewers.
"""

USABILITY = """# Usability task test (five people) and 30-day household pilot

## Five-person task test
Recruit five people who resemble the pilot customer (buying or just bought an older Allegheny County house) and are
strangers to the project. Use a synthetic house unless the participant consents to use their own record. No help is given
during tasks; note where they stall.

| # | Task | Pass criterion | Target |
|---|------|----------------|--------|
| 1 | Open the Plan page. Say which action you'd do first and why. | Names the first item and gives the shown reason, within 2 minutes | 4 of 5 |
| 2 | The record says the house has a fireplace, but it is sealed. Correct that. | Finds the question or record form, records "chimney not in use", and sees the chimney task leave the list | 4 of 5 |
| 3 | For any task, say whether it comes from a documented finding, general guidance, or missing information. | Uses the tags/"Why, evidence and source" and answers correctly | 4 of 5 |
| 4 | Mark a task done, or produce a job brief for a professional. | Completes without assistance | 4 of 5 |

Record time-on-task, errors, and verbatim confusion for each participant.

## 30-day household pilot log
One row per household. Target: at least half complete one relevant action within 30 days.

| household | start | actions completed (ids) | dismissals (id, reason category: irrelevant / already done / someone else / other) | snoozes | corrections made | notes |
|-----------|-------|--------------------------|-------------------------------------------------------------------------------------|---------|------------------|-------|
|           |       |                          |                                                                                     |         |                  |       |

Dismissal reasons are categorised from the reason text the app requires, not inferred.
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--house", action="append", default=[], help="house id of a REAL, CONSENTED record to include")
    a = ap.parse_args(argv)
    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "houses").mkdir(parents=True, exist_ok=True)
    rec_rows, eq_rows, included = [], [], []
    for p in synthetic_houses():
        r, q = rows_for(p, "dev")
        rec_rows += r; eq_rows += q; included.append({"house_id": p.house_id, "synthetic": True, "set": "dev", "rows": len(r)})
        shutil.copy(HOUSES / f"{p.house_id}.json", OUT / "houses" / f"{p.house_id}.json")
    for i, hid in enumerate(a.house):
        p = Profile.load(hid)
        set_name = "dev" if i % 2 == 0 else "holdout"
        r, q = rows_for(p, set_name)
        rec_rows += r; eq_rows += q; included.append({"house_id": hid, "synthetic": p.synthetic, "set": set_name, "rows": len(r)})
        shutil.copy(HOUSES / f"{hid}.json", OUT / "houses" / f"{hid}.json")
    write_csv(OUT / "recommendations_review.csv", REC_COLS, rec_rows)
    write_csv(OUT / "omissions_review.csv", OMIT_COLS, [])
    write_csv(OUT / "equipment_rule_check.csv", EQ_COLS, eq_rows)
    shutil.copy(ROOT / "audit" / "provider_match_review.csv", OUT / "provider_match_review.csv")
    (OUT / "README.md").write_text(README, encoding="utf-8")
    (OUT / "usability_tasks.md").write_text(USABILITY, encoding="utf-8")
    sources = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    manifest = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S"), "app_version": VERSION,
                "rule_count": len(rules.load_rules()), "rule_versions": {r["id"]: r["version"] for r in rules.load_rules()},
                "sources_audited": sources.get("audited"), "houses": included,
                "recommendation_rows": len(rec_rows), "equipment_rows": len(eq_rows),
                "status": "UNFILLED — reviewer columns empty; establishes nothing until reviewed"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"benchmark written to {OUT}: {len(rec_rows)} recommendation rows, {len(eq_rows)} equipment rows, "
          f"{len(included)} houses ({sum(1 for h in included if h['synthetic'])} synthetic). Reviewer columns are empty.")


if __name__ == "__main__":
    main()
