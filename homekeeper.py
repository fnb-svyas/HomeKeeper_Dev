#!/usr/bin/env python3
"""HomeKeeper prototype — command-line entry point (Checkpoint 2: house-profile builder).

Usage (Windows, from the project folder):
  python homekeeper.py doctor                      # live checks of every data endpoint
  python homekeeper.py build "123 Any St, Pittsburgh, PA 15228"
  python homekeeper.py build "..." --choose 1     # pick a candidate when the match was ambiguous
  python homekeeper.py show <house-id>
  python homekeeper.py plan <house-id>             # provisional plan + open questions
  python homekeeper.py answer <house-id> <field> <value>   # owner answer/correction (provenance kept)
  python homekeeper.py equipment <house-id> furnace --make Goodman --model GMVC96 --year 2019 --manual goodman_rs6612023
  python homekeeper.py finding <house-id> roof major "Lifted shingles at rear slope" --recommendation "roofer to evaluate" --date 2026-10-20
  python homekeeper.py responsibility <house-id> roof HOA --reason "condo association owns the roof"
  python homekeeper.py report buy|plan90|next|calendar|budget|all <house-id>
  python homekeeper.py report fit <house-id> --hours 2 --dollars 200
  python homekeeper.py quote <house-id> FINDING-f-001 450 900 --scope "replace lifted shingles, rear slope" --source "ABC Roofing 2026-10-25"
  python homekeeper.py reserve <house-id> water_heater 5 1500 2800 --basis planning_assumption
  python homekeeper.py done <house-id> R-HEAT-001 --date 2026-10-20 --cost 165 --contractor "Keystone HVAC" --notes "CO 3 ppm"
  python homekeeper.py snooze <house-id> R-GUTTER-001 2026-11-20 --reason "leaves not down yet"
  python homekeeper.py dismiss <house-id> R-DRYER-001 "no dryer; laundromat"
  python homekeeper.py document <house-id> invoice "Furnace service 2026" "C:\\Users\\me\\House\\furnace-2026.pdf" --component furnace
  python homekeeper.py brief <house-id> FINDING-f-001 --show
  python homekeeper.py history <house-id>
  python homekeeper.py reminders export <house-id>      # writes houses/<id>/reminders.ics for your calendar app
  python homekeeper.py reminders list <house-id> --days 90
  python homekeeper.py sample complete|missing|ambiguous   # offline synthetic demos
  python homekeeper.py list

Standard library only. No API keys. Network calls are cached under cache/.
"""
from __future__ import annotations

import argparse
import json
import sys

from hk import VERSION, actions, briefs, budget, builder, http, providers, questions, reminders, report, reports, rules, samples
from hk.evidence import Profile


def cmd_doctor(_):
    from hk import doctor
    doctor.run()


def cmd_build(a):
    p = builder.build(a.address, house_id=a.id, choose=a.choose)
    print(report.render_profile(p))
    _plan(p)


def cmd_sample(a):
    addr = samples.install(a.name)
    p = builder.build(addr, house_id=f"sample-{a.name}", mode="offline-sample", synthetic=True, choose=a.choose)
    print(report.render_profile(p))
    _plan(p)


def _plan(p: Profile, top: int = 3):
    tasks = rules.evaluate(p)
    print(report.render_tasks(tasks, top=top))
    print(report.render_questions(questions.pending(p, tasks)))


def _diff(p: Profile, fn, label: str):
    before = {t.rule_id: t.status for t in rules.evaluate(p)}
    fn()
    p.save()
    after = {t.rule_id: t.status for t in rules.evaluate(p)}
    changed = [(rid, before.get(rid, "—"), after[rid]) for rid in after if before.get(rid) != after[rid]]
    changed += [(rid, before[rid], "—") for rid in before if rid not in after]
    print(label)
    if changed:
        print("recommendations changed:")
        for rid, b, c in changed:
            print(f"  {rid}: {b} -> {c}")
    else:
        print("no recommendation changed")


def cmd_equipment(a):
    import time
    p = Profile.load(a.id)

    def do():
        e = p.add_equipment(a.component, make=a.make or "", model=a.model or "", installed_year=a.year,
                            manual_source_id=a.manual, note=a.note or "")
        if a.year and a.component in ("roof", "water_heater", "furnace", "ac", "sump_pump"):
            # keep the profile field in step with the equipment record (provenance: the equipment entry)
            p.correct(f"{a.component}_installed_year", a.year, source_id=f"equipment:{e['id']}",
                      reason=f"from equipment record {e['id']}", status="owner_confirmed")
        if a.year and a.year >= int(time.strftime("%Y")):
            # a current-year install may still be inside its warranty-registration window
            p.correct("new_equipment_pending_registration", True, reason=f"{a.component} installed {a.year}; confirm registration",
                      status="owner_confirmed")
    _diff(p, do, f"recorded {a.component}: {a.make or ''} {a.model or ''} installed {a.year or '?'} (manual: {a.manual or 'none'})")


def cmd_finding(a):
    p = Profile.load(a.id)
    _diff(p, lambda: p.add_finding(a.component, a.severity, a.description, recommendation=a.recommendation or "",
                                   source_doc=a.source or "inspection report", observed_date=a.date, location=a.location or ""),
          f"recorded {a.severity} finding on {a.component}")


def cmd_responsibility(a):
    p = Profile.load(a.id)
    party = None if a.party.lower() in ("homeowner", "me", "none") else a.party
    _diff(p, lambda: p.set_responsibility(a.component, party, a.reason or ""),
          f"{a.component} responsibility -> {party or 'homeowner'}")


def cmd_show(a):
    p = Profile.load(a.id)
    print(report.render_profile(p))


def cmd_plan(a):
    p = Profile.load(a.id)
    _plan(p)


def cmd_answer(a):
    p = Profile.load(a.id)
    kind = next((k for n, _, _, k in questions.ONBOARDING if n == a.field), "text")
    try:
        value = questions.parse_answer(kind, a.value)
    except ValueError as e:
        sys.exit(f"could not parse {a.value!r} as {kind}: {e}")
    before = {t.rule_id: t.status for t in rules.evaluate(p)}
    builder.apply_answer(p, a.field, value, reason=a.reason or "owner answer")
    after = {t.rule_id: t.status for t in rules.evaluate(p)}
    changed = [(rid, before[rid], after[rid]) for rid in after if before.get(rid) != after[rid]]
    print(f"recorded {a.field} = {value!r} (source: owner) for {p.house_id}")
    if changed:
        print("recommendations changed:")
        for rid, b, c in changed:
            print(f"  {rid}: {b} -> {c}")
    else:
        print("no recommendation changed")


def cmd_report(a):
    p = Profile.load(a.id)
    tasks = rules.evaluate(p)
    kind = a.kind
    if kind == "buy":
        print(reports.before_you_buy(p, tasks))
    elif kind == "plan90":
        print(reports.first_90_days(p, tasks))
    elif kind == "next":
        print(reports.next_three(p, tasks))
    elif kind == "calendar":
        print(reports.calendar(p, tasks))
    elif kind == "budget":
        print(budget.render_budgets(budget.build_budgets(p, tasks)))
    elif kind == "fit":
        print(reports.constrained(p, tasks, hours=a.hours, dollars=a.dollars))
    elif kind == "all":
        for fn in (reports.before_you_buy, reports.first_90_days, reports.next_three, reports.calendar):
            print(fn(p, tasks)); print("\n" + "=" * 100 + "\n")
        print(budget.render_budgets(budget.build_budgets(p, tasks)))


def cmd_quote(a):
    p = Profile.load(a.id)
    e = budget.add_estimate(p, applies_to=a.applies_to, low=a.low, high=a.high, basis=a.basis, scope=a.scope,
                            exclusions=a.exclusions or "", geo=a.geo, source=a.source or "", date=a.date, note=a.note or "")
    p.save()
    print(f"recorded {e['id']}: {a.applies_to} ${a.low:,.0f}–${a.high:,.0f} [{a.basis}; {e['source']} {e['date']}]")


def cmd_reserve(a):
    p = Profile.load(a.id)
    r = budget.set_reserve(p, component=a.component, years=a.years, low=a.low, high=a.high, basis=a.basis,
                           source=a.source or "", note=a.note or "")
    p.save()
    print(f"reserve scenario: {a.component} ${a.low:,.0f}–${a.high:,.0f} over {a.years} years "
          f"= ${a.low/(a.years*12):,.0f}–${a.high/(a.years*12):,.0f}/month [{a.basis}]")


def _task(p: Profile, rule_id: str):
    for t in rules.evaluate(p):
        if t.rule_id == rule_id:
            return t
    sys.exit(f"no task {rule_id!r} for {p.house_id} (use 'plan' to list ids)")


def cmd_done(a):
    p = Profile.load(a.id)
    t = _task(p, a.task)
    rv = next((r["version"] for r in rules.load_rules() if r["id"] == a.task), 0)
    _diff(p, lambda: actions.complete(p, a.task, date=a.date, notes=a.notes or "", cost=a.cost, contractor=a.contractor or "",
                                      documents=a.doc or [], component=t.component, rule_version=rv),
          f"completed {a.task} on {a.date or 'today'}" + (f" (${a.cost:,.0f})" if a.cost is not None else ""))
    nxt = next((t for t in rules.evaluate(p) if t.rule_id == a.task), None)
    print("  next:", (nxt.due if nxt else "resolved — now in the house history") or "—")


def cmd_snooze(a):
    p = Profile.load(a.id)
    _task(p, a.task)
    _diff(p, lambda: actions.snooze(p, a.task, a.until, a.reason or ""), f"snoozed {a.task} until {a.until} (not counted as done)")


def cmd_dismiss(a):
    p = Profile.load(a.id)
    _task(p, a.task)
    _diff(p, lambda: actions.does_not_apply(p, a.task, a.reason), f"{a.task}: does not apply — {a.reason}")
    print("  if this is because the house record is wrong, correct it instead: answer <id> <field> <value>")


def cmd_reopen(a):
    p = Profile.load(a.id)
    _diff(p, lambda: actions.reopen(p, a.task, a.reason or ""), f"reopened {a.task}")


def cmd_document(a):
    p = Profile.load(a.id)
    d = actions.add_document(p, kind=a.kind, title=a.title, ref=a.ref, component=a.component or "", rule_id=a.task or "",
                             date=a.date, note=a.note or "")
    p.save()
    print(f"recorded {d['id']} ({a.kind}): {a.title} -> {a.ref}")


def cmd_history(a):
    print(actions.history(Profile.load(a.id)))


def cmd_brief(a):
    p = Profile.load(a.id)
    t = _task(p, a.task)
    path = briefs.write_brief(p, t)
    p.save()
    print(f"wrote editable job brief: {path}")
    if a.show:
        print(); print(path.read_text(encoding="utf-8"))


def cmd_purge(a):
    p = Profile.load(a.id)
    if not a.yes:
        sys.exit("this removes documents, completions, findings, estimates and owner answers from the record; re-run with --yes")
    n = actions.purge_private(p)
    p.save()
    print("purged:", n)


def cmd_providers(a):
    store = providers.load()
    if a.pcmd == "discover":
        fields, r = providers.discover_fields(providers.ACHD_PLUMBERS_RESOURCE)
        print("ACHD plumbers fields:", fields or r.reason)
        res = http.fetch(providers.CITY_TRADES_PACKAGE, max_age_days=0)
        if res.ok and isinstance(res.data, dict) and res.data.get("success"):
            for x in res.data["result"].get("resources", []):
                print(f"City trades resource: {x.get('name')}  id={x.get('id')}  datastore={x.get('datastore_active')}")
        else:
            print("City trades package:", res.reason)
    elif a.pcmd == "import":
        if a.source == "achd":
            print(json.dumps(providers.import_achd_plumbers(store), indent=2, default=str)[:3000])
        elif a.source == "city":
            print(json.dumps(providers.import_city_trade_licenses(store, resource_id=a.resource), indent=2, default=str)[:3000])
        elif a.source == "radon":
            if not a.file or not a.date:
                sys.exit("usage: providers import radon <csv> --date YYYY-MM-DD")
            print(providers.import_radon_csv(store, a.file, a.date))
        providers.save(store)
    elif a.pcmd == "add":
        rec = providers.add_manual(store, name=a.name, categories=[a.category], address=a.address or "", phone=a.phone or "",
                                   service_area=a.area, note=a.note or "")
        providers.save(store); print(f"added {rec['id']}: {rec['name']} ({a.category}); credentials: none yet")
    elif a.pcmd == "verify":
        pr = next((x for x in store if x["id"] == a.pid), None) or sys.exit(f"no provider {a.pid}")
        c = providers.add_credential(pr, ctype=a.ctype, identifier=a.identifier or "", status=a.status or "", date=a.date,
                                     source_id=a.source or "", url=a.url or "")
        providers.save(store); print(f"{pr['name']}: {providers.wording(c)}")
    elif a.pcmd == "geocode":
        n = sum(1 for pr in store if providers.geocode_provider(pr)); providers.save(store); print(f"geocoded {n} provider(s)")
    elif a.pcmd == "list":
        for pr in store:
            print(f"{pr['id']}  {pr['name']:<40} {', '.join(pr.get('categories', [])):<20} creds={len(pr.get('credentials', []))}"
                  + ("  [SYNTHETIC]" if pr.get("synthetic") else ""))
    elif a.pcmd == "match":
        p = Profile.load(a.house)
        t = _task(p, a.task)
        print(providers.render_match(providers.match(p, t, store), p))


def cmd_reminders(a):
    p = Profile.load(a.id)
    if a.rcmd == "export":
        path = reminders.export(p)
        n = len(reminders.build_events(p))
        print(f"wrote {path} ({n} events, next 12 months). Import or subscribe to it in your calendar app.")
        print(reminders.METHOD_STATEMENT)
    elif a.rcmd == "list":
        print(reminders.render_upcoming(p, days=a.days))
    elif a.rcmd == "method":
        print(reminders.METHOD_STATEMENT)


def cmd_list(_):
    for hid in Profile.list_ids():
        print(hid)


def cmd_export(a):
    p = Profile.load(a.id)
    print(json.dumps(p.to_dict(), indent=2))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="homekeeper", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=VERSION)
    ap.add_argument("--offline", action="store_true", help="never touch the network (use cache/fixtures only)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor").set_defaults(fn=cmd_doctor)
    b = sub.add_parser("build"); b.add_argument("address"); b.add_argument("--id"); b.add_argument("--choose", type=int)
    b.set_defaults(fn=cmd_build)
    s = sub.add_parser("sample"); s.add_argument("name", choices=sorted(samples.SAMPLES)); s.add_argument("--choose", type=int)
    s.set_defaults(fn=cmd_sample)
    sh = sub.add_parser("show"); sh.add_argument("id"); sh.set_defaults(fn=cmd_show)
    pl = sub.add_parser("plan"); pl.add_argument("id"); pl.set_defaults(fn=cmd_plan)
    an = sub.add_parser("answer"); an.add_argument("id"); an.add_argument("field"); an.add_argument("value")
    an.add_argument("--reason", default=""); an.set_defaults(fn=cmd_answer)
    eq = sub.add_parser("equipment", help="record identified equipment (a replacement retires the old entry)")
    eq.add_argument("id"); eq.add_argument("component", help="furnace|ac|water_heater|sump_pump|roof|...")
    eq.add_argument("--make"); eq.add_argument("--model"); eq.add_argument("--year", type=int)
    eq.add_argument("--manual", help="source id of the manual in data/sources.json, e.g. goodman_rs6612023")
    eq.add_argument("--note"); eq.set_defaults(fn=cmd_equipment)
    fi = sub.add_parser("finding", help="record a documented finding from an inspection report")
    fi.add_argument("id"); fi.add_argument("component"); fi.add_argument("severity", choices=["safety", "major", "minor", "info"])
    fi.add_argument("description"); fi.add_argument("--recommendation"); fi.add_argument("--source"); fi.add_argument("--date")
    fi.add_argument("--location"); fi.set_defaults(fn=cmd_finding)
    rs = sub.add_parser("responsibility", help="assign a component to another party (HOA, landlord) or back to homeowner")
    rs.add_argument("id"); rs.add_argument("component"); rs.add_argument("party"); rs.add_argument("--reason")
    rs.set_defaults(fn=cmd_responsibility)
    rp = sub.add_parser("report", help="buy | plan90 | next | calendar | budget | fit | all")
    rp.add_argument("kind", choices=["buy", "plan90", "next", "calendar", "budget", "fit", "all"]); rp.add_argument("id")
    rp.add_argument("--hours", type=float, default=2.0); rp.add_argument("--dollars", type=float, default=200.0)
    rp.set_defaults(fn=cmd_report)
    qt = sub.add_parser("quote", help="record a cost estimate for a rule id or component")
    qt.add_argument("id"); qt.add_argument("applies_to", help="rule id (R-...) or component (roof, water_heater, ...)")
    qt.add_argument("low", type=float); qt.add_argument("high", type=float)
    qt.add_argument("--basis", choices=budget.BASES, default="user_quote"); qt.add_argument("--scope", required=True)
    qt.add_argument("--exclusions"); qt.add_argument("--geo", default="Allegheny County, PA"); qt.add_argument("--source")
    qt.add_argument("--date"); qt.add_argument("--note"); qt.set_defaults(fn=cmd_quote)
    rv = sub.add_parser("reserve", help="choose a replacement reserve scenario: component, years, cost range")
    rv.add_argument("id"); rv.add_argument("component"); rv.add_argument("years", type=int)
    rv.add_argument("low", type=float); rv.add_argument("high", type=float)
    rv.add_argument("--basis", choices=budget.BASES, default="planning_assumption"); rv.add_argument("--source"); rv.add_argument("--note")
    rv.set_defaults(fn=cmd_reserve)
    dn = sub.add_parser("done", help="record a completion (advances recurring tasks; 'already completed' = pass --date)")
    dn.add_argument("id"); dn.add_argument("task", help="rule id (R-...) or FINDING-f-...")
    dn.add_argument("--date"); dn.add_argument("--notes"); dn.add_argument("--cost", type=float); dn.add_argument("--contractor")
    dn.add_argument("--doc", action="append", help="document id(s) to attach"); dn.set_defaults(fn=cmd_done)
    sn = sub.add_parser("snooze"); sn.add_argument("id"); sn.add_argument("task"); sn.add_argument("until"); sn.add_argument("--reason")
    sn.set_defaults(fn=cmd_snooze)
    ds = sub.add_parser("dismiss", help="mark a task 'does not apply' (reason required; never counts as done)")
    ds.add_argument("id"); ds.add_argument("task"); ds.add_argument("reason"); ds.set_defaults(fn=cmd_dismiss)
    ro = sub.add_parser("reopen"); ro.add_argument("id"); ro.add_argument("task"); ro.add_argument("--reason"); ro.set_defaults(fn=cmd_reopen)
    dc = sub.add_parser("document", help="record a document reference (invoice, manual, warranty, photo, report)")
    dc.add_argument("id"); dc.add_argument("kind", choices=["invoice", "manual", "warranty", "photo", "report", "permit", "other"])
    dc.add_argument("title"); dc.add_argument("ref", help="file path or URL where you keep it"); dc.add_argument("--component")
    dc.add_argument("--task"); dc.add_argument("--date"); dc.add_argument("--note"); dc.set_defaults(fn=cmd_document)
    hs = sub.add_parser("history"); hs.add_argument("id"); hs.set_defaults(fn=cmd_history)
    br = sub.add_parser("brief", help="write an editable contractor job brief for a task")
    br.add_argument("id"); br.add_argument("task"); br.add_argument("--show", action="store_true"); br.set_defaults(fn=cmd_brief)
    pg = sub.add_parser("purge", help="remove private information from a house record"); pg.add_argument("id"); pg.add_argument("--yes", action="store_true")
    pg.set_defaults(fn=cmd_purge)
    pv = sub.add_parser("providers", help="provider inventory: discover | import | add | verify | geocode | list | match")
    pvs = pv.add_subparsers(dest="pcmd", required=True)
    pvs.add_parser("discover"); pvs.add_parser("geocode"); pvs.add_parser("list")
    pi = pvs.add_parser("import"); pi.add_argument("source", choices=["achd", "city", "radon"]); pi.add_argument("file", nargs="?")
    pi.add_argument("--date"); pi.add_argument("--resource")
    pa_ = pvs.add_parser("add"); pa_.add_argument("name"); pa_.add_argument("category"); pa_.add_argument("--address"); pa_.add_argument("--phone")
    pa_.add_argument("--area", action="append"); pa_.add_argument("--note")
    pvf = pvs.add_parser("verify"); pvf.add_argument("pid"); pvf.add_argument("ctype", choices=sorted(providers.CREDENTIAL_WORDING))
    pvf.add_argument("--identifier"); pvf.add_argument("--status"); pvf.add_argument("--date"); pvf.add_argument("--source"); pvf.add_argument("--url")
    pm = pvs.add_parser("match"); pm.add_argument("house"); pm.add_argument("task")
    pv.set_defaults(fn=cmd_providers)
    rm = sub.add_parser("reminders", help="export | list | method")
    rms = rm.add_subparsers(dest="rcmd", required=True)
    rx = rms.add_parser("export"); rx.add_argument("id")
    rl = rms.add_parser("list"); rl.add_argument("id"); rl.add_argument("--days", type=int, default=90)
    rms.add_parser("method")
    rm.set_defaults(fn=cmd_reminders)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    ex = sub.add_parser("export"); ex.add_argument("id"); ex.set_defaults(fn=cmd_export)
    a = ap.parse_args(argv)
    if a.offline:
        http.set_offline(True)
    a.fn(a)


if __name__ == "__main__":
    main()
