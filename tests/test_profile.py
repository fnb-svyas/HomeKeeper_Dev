"""Checkpoint 2 software checks (offline, synthetic fixtures). Run: python -m unittest -v"""
import json
import shutil
import unittest

from hk import HOUSES, builder, http, questions, rules, samples
from hk.evidence import Field, Profile


class EvidenceModel(unittest.TestCase):
    def test_unknown_is_explicit_and_never_false(self):
        f = Field(name="sump_pump_present", value=None)
        self.assertTrue(f.is_unknown)
        self.assertEqual(f.evidence_type, "unknown")
        self.assertIsNot(f.value, False)

    def test_correction_keeps_provenance(self):
        p = Profile(house_id="t-prov", address_input="x", synthetic=True)
        p.set(Field(name="basement", value="Full", source_id="wprdc_assessments", source_ref="col BASEMENTDESC",
                    evidence_type="public_record", verification_status="unverified"))
        p.correct("basement", "Part", reason="inspection")
        f = p.get("basement")
        self.assertEqual(f.value, "Part")
        self.assertEqual(f.evidence_type, "owner_reported")
        self.assertEqual(f.history[0]["value"], "Full")
        self.assertEqual(f.conflicts[0]["source_id"], "wprdc_assessments")

    def test_roundtrip_json(self):
        p = Profile(house_id="t-rt", address_input="x", synthetic=True)
        p.set(Field(name="year_built", value=1928, source_id="wprdc_assessments", evidence_type="public_record",
                    verification_status="unverified"))
        d = json.loads(json.dumps(p.to_dict()))
        self.assertEqual(Profile.from_dict(d).value("year_built"), 1928)


class Samples(unittest.TestCase):
    def setUp(self):
        http.clear_fixtures(); http.set_offline(True)

    def test_complete_profile_fields_are_source_tagged(self):
        p = builder.build(samples.install("complete"), house_id="t-complete", synthetic=True)
        self.assertEqual(p.value("year_built"), 1928)
        self.assertEqual(p.get("year_built").source_id, "wprdc_assessments")
        self.assertEqual(p.get("radon_zip_stats").evidence_type, "regional_exposure")
        self.assertTrue(p.value("undermined"))
        self.assertTrue(p.value("point_of_sale_sewer_rule")["required_at_sale"])

    def test_missing_info_stays_visible(self):
        p = builder.build(samples.install("missing"), house_id="t-missing", synthetic=True)
        self.assertTrue(p.get("year_built").is_unknown)
        self.assertTrue(p.get("flood_zone").is_unknown)
        self.assertIn("not retrieved", p.get("flood_zone").note)
        tasks = {t.rule_id: t for t in rules.evaluate(p)}
        self.assertEqual(tasks["R-LEAD-001"].status, "needs_info")
        self.assertEqual(tasks["R-FLOOD-001"].status, "not_applicable")
        self.assertEqual(tasks["R-MSI-001"].status, "applies")

    def test_ambiguous_match_is_not_silently_chosen(self):
        p = builder.build(samples.install("ambiguous"), house_id="t-amb", synthetic=True)
        self.assertTrue(p.match["ambiguous"]); self.assertIsNone(p.match["chosen"])
        p2 = builder.build(samples.install("ambiguous"), house_id="t-amb2", synthetic=True, choose=1)
        self.assertEqual(p2.match["chosen"], 1); self.assertTrue(p2.match["owner_confirmed"])

    def test_correction_changes_recommendation(self):
        p = builder.build(samples.install("complete"), house_id="t-corr", synthetic=True)
        before = {t.rule_id: t.status for t in rules.evaluate(p)}
        self.assertEqual(before["R-HEAT-001"], "needs_info")
        self.assertEqual(before["R-ROOF-001"], "applies")
        builder.apply_answer(p, "heating_fuel", "electric")
        builder.apply_answer(p, "roof_installed_year", 2009)
        after = {t.rule_id: t.status for t in rules.evaluate(p)}
        self.assertEqual(after["R-HEAT-001"], "excluded")
        self.assertEqual(after["R-ROOF-001"], "not_triggered")
        self.assertEqual(after["R-ROOF-002"], "applies")

    def test_questions_only_ask_unknowns_and_name_what_they_unblock(self):
        p = builder.build(samples.install("complete"), house_id="t-q", synthetic=True)
        qs = questions.pending(p, rules.evaluate(p))
        fields = [q["field"] for q in qs]
        self.assertIn("heating_fuel", fields)
        self.assertNotIn("year_built", fields)
        self.assertIn("R-HEAT-001", next(q for q in qs if q["field"] == "heating_fuel")["unblocks"])

    def test_dismissed_or_unknown_answer_is_not_treated_as_done(self):
        p = builder.build(samples.install("complete"), house_id="t-none", synthetic=True)
        builder.apply_answer(p, "radon_result_date", None)
        self.assertTrue(p.get("radon_result_date").is_unknown)
        self.assertEqual({t.rule_id: t.status for t in rules.evaluate(p)}["R-RADON-001"], "applies")

    @classmethod
    def tearDownClass(cls):
        for f in HOUSES.glob("t-*.json"):
            try:
                f.unlink()
            except OSError:
                pass  # some sandboxes forbid deletes; leftover test profiles are harmless


class RuleEngine(unittest.TestCase):
    def test_every_rule_cites_a_registered_source(self):
        from hk import sources
        for r in rules.load_rules():
            sources.get(r["source_id"])
            self.assertTrue(r["source_ref"])
            self.assertIn(r["when_unknown"], ("ask", "verify", "apply", "skip"))

    def test_exclusion_beats_trigger(self):
        p = Profile(house_id="t-ex", address_input="x", synthetic=True)
        p.set(Field(name="heating_fuel", value="heat pump", source_id="owner", evidence_type="owner_reported",
                    verification_status="owner_confirmed"))
        t = {t.rule_id: t for t in rules.evaluate(p)}["R-HEAT-001"]
        self.assertEqual(t.status, "excluded")


if __name__ == "__main__":
    unittest.main()


class Checkpoint3(unittest.TestCase):
    def setUp(self):
        http.clear_fixtures(); http.set_offline(True)
        self.p = builder.build(samples.install("complete"), house_id="t-cp3", synthetic=True)

    def statuses(self):
        return {t.rule_id: t for t in rules.evaluate(self.p)}

    def test_rule_schema_and_sources(self):
        from hk import sources
        for r in rules.load_rules():
            for k in ("id", "version", "component", "task_category", "trigger", "exclusions", "required_fields",
                      "when_unknown", "action", "why", "recurrence", "severity", "priority_rationale", "diy_pro",
                      "completion_criteria", "cost", "source_id", "source_ref", "review_status", "review_date"):
                self.assertIn(k, r, f"{r['id']} missing {k}")
            sources.get(r["source_id"])
            for sid in (r.get("variants") or {}):
                sources.get(sid)
            self.assertIn(r["recurrence"]["type"], ("one_time", "fixed_date", "seasonal_window",
                                                     "interval_since_completion", "equipment_interval", "event"))

    def test_applies_from_public_record(self):
        self.assertEqual(self.statuses()["R-CHIM-001"].status, "applies")
        self.assertEqual(self.statuses()["R-LEAD-001"].status, "applies")

    def test_excluded_by_confirmed_information(self):
        builder.apply_answer(self.p, "heating_fuel", "heat pump")
        builder.apply_answer(self.p, "chimney_in_use", False)
        s = self.statuses()
        self.assertEqual(s["R-HEAT-001"].status, "excluded")
        self.assertEqual(s["R-CHIM-001"].status, "excluded")

    def test_requires_verification(self):
        t = self.statuses()["R-SUMP-001"]
        self.assertEqual(t.status, "verification")
        self.assertIn("sump pit", t.action)

    def test_generic_refined_by_equipment_manual(self):
        builder.apply_answer(self.p, "heating_type", "forced air")
        before = self.statuses()["R-HEAT-002"]
        self.assertEqual(before.recurrence["months"], 1)
        self.p.add_equipment("furnace", make="Goodman", model="GMVC96", installed_year=2019,
                             manual_source_id="goodman_rs6612023")
        after = self.statuses()["R-HEAT-002"]
        self.assertEqual(after.recurrence["months"], 2)
        self.assertIn("goodman_rs6612023", [s["source_id"] for s in after.sources])
        self.assertIn("doe_energysaver", [s["source_id"] for s in after.sources])  # generic source kept

    def test_replacement_changes_task(self):
        builder.apply_answer(self.p, "water_heater_type", "tank")
        builder.apply_answer(self.p, "water_heater_installed_year", 2012)
        self.assertEqual(self.statuses()["R-WH-002"].status, "applies")
        e = self.p.add_equipment("water_heater", make="A. O. Smith", installed_year=2026, manual_source_id="aosmith_100398943")
        self.p.correct("water_heater_installed_year", 2026, source_id=f"equipment:{e['id']}")
        s = self.statuses()
        self.assertEqual(s["R-WH-002"].status, "not_triggered")
        self.assertIn("A. O. Smith", s["R-WH-001"].refined_by)
        self.assertEqual(self.p.get("water_heater_installed_year").history[-1]["value"], 2012)

    def test_hoa_responsibility_removes_work(self):
        self.p.add_finding("roof", "major", "Lifted shingles at rear slope", source_doc="inspection report p.14")
        top = rules.prioritize(rules.evaluate(self.p))[0]
        self.assertEqual(top.status, "finding")
        self.p.set_responsibility("roof", "HOA", "declaration 4.2")
        s = self.statuses()
        self.assertEqual(s["R-ROOF-003"].status, "someone_else")
        self.assertEqual(s["FINDING-f-001"].status, "someone_else")
        self.assertNotIn("FINDING-f-001", [t.rule_id for t in rules.prioritize(rules.evaluate(self.p))])

    def test_recurrence_dates(self):
        import datetime as dt
        label, days = rules.due_label({"type": "interval_since_completion", "months": 12},
                                      last_done="2025-02-28", today=dt.date(2026, 10, 29))
        self.assertTrue(label.startswith("overdue since 2026-02-28"))
        label, _ = rules.due_label({"type": "interval_since_completion", "months": 1},
                                   last_done="2024-01-31", today=dt.date(2024, 2, 15))
        self.assertIn("2024-02-29", label)  # leap-year safe month arithmetic
        label, days = rules.due_label({"type": "fixed_date", "date": "10-15"}, today=dt.date(2026, 10, 29))
        self.assertIn("2027-10-15", label)

    def test_merge_dedupes_same_key(self):
        builder.apply_answer(self.p, "heating_fuel", "gas")
        builder.apply_answer(self.p, "heating_type", "boiler")
        ids = [t.rule_id for t in rules.prioritize(rules.evaluate(self.p))]
        self.assertIn("R-HEAT-003", ids)
        self.assertEqual(self.statuses()["R-HEAT-002"].status, "excluded")

    @classmethod
    def tearDownClass(cls):
        for f in HOUSES.glob("t-*.json"):
            try:
                f.unlink()
            except OSError:
                pass


class Checkpoint4(unittest.TestCase):
    def setUp(self):
        from hk import budget, reports
        self.budget, self.reports = budget, reports
        http.clear_fixtures(); http.set_offline(True)
        self.p = builder.build(samples.install("complete"), house_id="t-cp4", synthetic=True)
        builder.apply_answer(self.p, "heating_fuel", "gas")
        builder.apply_answer(self.p, "heating_type", "forced air")
        self.p.add_finding("roof", "major", "Lifted shingles at rear slope", source_doc="inspection report p.14")
        builder.apply_answer(self.p, "roof_installed_year", 2008)

    def tasks(self):
        return rules.evaluate(self.p)

    def test_budgets_never_invent_prices(self):
        b = self.budget.build_budgets(self.p, self.tasks())
        self.assertEqual(b["repairs"], [])            # finding has no quote -> not priced
        self.assertEqual(b["replacements"], [])       # roof planning has no reserve -> not priced
        self.assertTrue(any(u["rule_id"] == "FINDING-f-001" for u in b["unknown"]))
        self.assertEqual(b["totals"]["repairs"], (0.0, 0.0))

    def test_quote_reserve_and_overlap(self):
        self.budget.add_estimate(self.p, applies_to="FINDING-f-001", low=450, high=900, basis="user_quote",
                                 scope="re-secure shingles", source="ABC Roofing")
        self.budget.set_reserve(self.p, component="roof", years=6, low=9000, high=16000, basis="planning_assumption")
        b = self.budget.build_budgets(self.p, self.tasks())
        self.assertEqual(b["totals"]["repairs"], (450.0, 900.0))
        r = b["replacements"][0]
        self.assertAlmostEqual(r["monthly_high"], 16000 / 72, places=2)
        self.assertIn("overlap_note", r)
        self.assertEqual(r["basis"], "planning_assumption")

    def test_routine_annualised(self):
        self.budget.add_estimate(self.p, applies_to="R-HEAT-001", low=120, high=220, basis="user_quote", scope="annual furnace service")
        b = self.budget.build_budgets(self.p, self.tasks())
        item = next(i for i in b["routine"] if i["rule_id"] == "R-HEAT-001")
        self.assertEqual(item["per_year"], 1.0); self.assertEqual((item["low"], item["high"]), (120.0, 220.0))

    def test_constrained_view_does_not_hide_urgent_items(self):
        txt = self.reports.constrained(self.p, self.tasks(), hours=0.25, dollars=0)
        self.assertIn("IMPORTANT ITEMS THAT DO NOT FIT", txt)
        self.assertIn("Lifted shingles", txt)

    def test_reports_consistent_with_profile(self):
        txt = self.reports.before_you_buy(self.p, self.tasks())
        self.assertIn("not an inspection", txt)
        self.assertIn("Lifted shingles", txt)
        self.assertRegex(txt, r"roof_installed_year\s+2008")
        cal = self.reports.calendar(self.p, self.tasks())
        self.assertIn("Annual professional inspection", cal)
        builder.apply_answer(self.p, "closing_date", "2026-11-14")
        p90 = self.reports.first_90_days(self.p, self.tasks())
        self.assertIn("from 2026-11-14", p90)
        self.assertIn("Week 1", p90)

    def test_next_three_fields(self):
        txt = self.reports.next_three(self.p, self.tasks())
        for s in ("why it applies", "what if you delay", "done when", "source:"):
            self.assertIn(s, txt)

    @classmethod
    def tearDownClass(cls):
        for f in HOUSES.glob("t-*.json"):
            try:
                f.unlink()
            except OSError:
                pass


class Checkpoint5(unittest.TestCase):
    def setUp(self):
        from hk import actions, briefs
        self.actions, self.briefs = actions, briefs
        http.clear_fixtures(); http.set_offline(True)
        self.p = builder.build(samples.install("complete"), house_id="t-cp5", synthetic=True)
        builder.apply_answer(self.p, "heating_fuel", "gas")
        builder.apply_answer(self.p, "heating_type", "forced air")
        self.p.add_finding("electrical", "safety", "Open junction box", source_doc="inspection p.22")

    def task(self, rid):
        return next((t for t in rules.evaluate(self.p) if t.rule_id == rid), None)

    def test_completion_advances_recurring_clock(self):
        self.assertTrue(self.task("R-HEAT-001").due.startswith("due now"))
        self.actions.complete(self.p, "R-HEAT-001", date="2026-10-20", cost=165, contractor="Keystone HVAC", component="heating")
        t = self.task("R-HEAT-001")
        self.assertIn("next due 2027-10-20", t.due)
        self.assertNotIn("R-HEAT-001", [x.rule_id for x in rules.prioritize(rules.evaluate(self.p))[:5]])

    def test_snooze_and_dismiss_are_not_done(self):
        self.actions.snooze(self.p, "R-GUTTER-001", "2099-01-01", "later")
        self.assertEqual(self.task("R-GUTTER-001").status, "snoozed")
        self.actions.does_not_apply(self.p, "R-DRYER-001", "no dryer")
        self.assertEqual(self.task("R-DRYER-001").status, "dismissed")
        self.assertFalse(any(c["rule_id"] in ("R-GUTTER-001", "R-DRYER-001") for c in self.p.completions))
        with self.assertRaises(ValueError):
            self.actions.does_not_apply(self.p, "R-WDI-001", "")
        self.actions.reopen(self.p, "R-GUTTER-001")
        self.assertEqual(self.task("R-GUTTER-001").status, "applies")

    def test_expired_snooze_reopens(self):
        self.actions.snooze(self.p, "R-GUTTER-001", "2000-01-01", "past")
        self.assertEqual(self.task("R-GUTTER-001").status, "applies")

    def test_finding_resolution_and_history(self):
        self.actions.complete(self.p, "FINDING-f-001", date="2026-11-21", cost=300, contractor="Spark Co", notes="box covered")
        self.assertIsNone(self.task("FINDING-f-001"))
        self.assertEqual(self.p.findings[0]["status"], "resolved")
        h = self.actions.history(self.p)
        self.assertIn("Spark Co", h); self.assertIn("$300", h)

    def test_completion_updates_equipment_service_date(self):
        self.p.add_equipment("furnace", make="Goodman", installed_year=2019, manual_source_id="goodman_rs6612023")
        self.actions.complete(self.p, "R-HEAT-001", date="2026-10-20", component="furnace")
        self.assertEqual(self.p.installed("furnace")["last_service_date"], "2026-10-20")

    def test_brief_has_no_diagnosis_and_lists_record_facts(self):
        self.actions.add_document(self.p, kind="photo", title="junction box photo", ref="photos/jbox.jpg", component="electrical")
        txt = self.briefs.brief_text(self.p, self.task("FINDING-f-001"))
        self.assertIn("Open junction box", txt); self.assertIn("junction box photo", txt)
        self.assertIn("nothing here is a diagnosis", txt)
        self.assertIn("Provider category: electrician", txt)

    def test_purge_removes_private_keeps_public(self):
        self.actions.add_document(self.p, kind="invoice", title="x", ref="y")
        n = self.actions.purge_private(self.p)
        self.assertEqual(n["documents"], 1)
        self.assertEqual(self.p.documents, []); self.assertEqual(self.p.findings, [])
        self.assertEqual(self.p.value("year_built"), 1928)
        self.assertTrue(self.p.get("heating_fuel").is_unknown)

    @classmethod
    def tearDownClass(cls):
        import shutil
        for f in HOUSES.glob("t-*"):
            try:
                shutil.rmtree(f) if f.is_dir() else f.unlink()
            except OSError:
                pass


class Checkpoint6(unittest.TestCase):
    def setUp(self):
        from hk import providers
        self.providers = providers
        http.clear_fixtures(); http.set_offline(True)
        self.p = builder.build(samples.install("complete"), house_id="t-cp6", synthetic=True)
        builder.apply_answer(self.p, "water_heater_type", "tank")
        self.store = providers.load()

    def task(self, rid):
        return next(t for t in rules.evaluate(self.p) if t.rule_id == rid)

    def test_synthetic_providers_hidden_for_real_houses(self):
        real = Profile(house_id="t-real", address_input="x", synthetic=False)
        m = self.providers.match(real, self.task("R-WH-001"), self.store)
        self.assertFalse(any(r["provider"].get("synthetic") for r in m["matches"]))  # real imports may exist on the pilot machine
        self.assertIn("HIRING CHECKLIST", m["checklist"])
        m2 = self.providers.match(real, self.task("R-WH-001"), [p for p in self.store if p.get("synthetic")])
        self.assertEqual(m2["matches"], [])

    def test_ranking_and_unknowns(self):
        m = self.providers.match(self.p, self.task("R-WH-001"), self.store)
        names = [r["provider"]["name"] for r in m["matches"]]
        self.assertTrue(names[0].startswith("Demo Plumbing"))      # serves + licensed + geocoded ranks first
        self.assertIsNone(m["matches"][1]["serves"])                # unknown stays None, not False
        txt = self.providers.render_match(m, self.p)
        self.assertIn("serves the address: unknown", txt)
        self.assertIn("workmanship: unknown", txt)
        self.assertNotIn("vetted", txt.lower())

    def test_wording_is_literal_and_dated(self):
        c = {"type": "achd_master_plumber", "identifier": "HP 12345", "status": "listed", "date": "2026-07-29"}
        self.assertEqual(self.providers.wording(c), "Allegheny County Health Department registered master plumber, HP 12345 (list dated 2026-07-29)")
        with self.assertRaises(AssertionError):
            self.providers.add_credential({}, ctype="licensed")

    def test_credential_relevance(self):
        m = self.providers.match(self.p, self.task("R-CHIM-001"), self.store)
        self.assertEqual([r["provider"]["name"] for r in m["matches"]][0], "Demo Chimney Sweeps (SYNTHETIC)")
        self.assertEqual(m["matches"][0]["credentials"][0]["type"], "csia")

    def test_manual_add_and_verify(self):
        store = []
        rec = self.providers.add_manual(store, name="Test Roofing", categories=["roofer"], service_area=["Mt. Lebanon"])
        self.providers.add_credential(rec, ctype="hicpa", identifier="PA000001", status="active", date="2026-11-02")
        m = self.providers.match(self.p, self.task("R-ROOF-003"), store)
        self.assertEqual(m["matches"][0]["serves"], True)
        self.assertIn("HICPA, PA000001, as checked 2026-11-02", self.providers.wording(m["matches"][0]["credentials"][0]))

    @classmethod
    def tearDownClass(cls):
        for f in HOUSES.glob("t-*.json"):
            try:
                f.unlink()
            except OSError:
                pass


class Checkpoint7(unittest.TestCase):
    def setUp(self):
        import datetime as dt
        from hk import actions, reminders
        self.dt, self.actions, self.rem = dt, actions, reminders
        http.clear_fixtures(); http.set_offline(True)
        self.p = builder.build(samples.install("complete"), house_id="t-cp7", synthetic=True)
        builder.apply_answer(self.p, "heating_fuel", "gas")
        builder.apply_answer(self.p, "heating_type", "forced air")
        self.today = dt.date(2026, 10, 29)

    def events(self):
        return self.rem.build_events(self.p, self.today)

    def test_ics_is_valid_and_stable(self):
        import re
        ics = self.rem.to_ics(self.p, self.events())
        lines = ics.split("\r\n")
        self.assertEqual(lines[0], "BEGIN:VCALENDAR"); self.assertEqual(lines[-2], "END:VCALENDAR")
        self.assertTrue(all(len(l.encode("utf-8")) <= 75 for l in lines))
        uids = re.findall(r"^UID:(.+)$", ics, re.M)
        self.assertEqual(len(uids), len(set(uids))); self.assertEqual(len(uids), ics.count("BEGIN:VEVENT"))
        self.assertEqual(set(uids), set(re.findall(r"^UID:(.+)$", self.rem.to_ics(self.p, self.events()), re.M)))

    def test_completion_moves_recurring_events(self):
        before = [e["date"] for e in self.events() if e["task"].rule_id == "R-HEAT-001"]
        self.assertEqual(before[0], self.today)
        self.actions.complete(self.p, "R-HEAT-001", date="2026-10-20", component="heating")
        after = [e["date"] for e in self.events() if e["task"].rule_id == "R-HEAT-001"]
        self.assertEqual(after, [self.dt.date(2027, 10, 20)])

    def test_snooze_dismiss_and_someone_else(self):
        self.actions.snooze(self.p, "R-GUTTER-001", "2026-11-20", "leaves")
        self.actions.does_not_apply(self.p, "R-WDI-001", "WDI report filed elsewhere")
        self.p.set_responsibility("chimney", "HOA")
        ev = {e["task"].rule_id: e for e in self.events()}
        self.assertEqual(ev["R-GUTTER-001"]["date"], self.dt.date(2026, 11, 20))
        self.assertNotIn("R-WDI-001", ev); self.assertNotIn("R-CHIM-001", ev)

    def test_no_duplicate_rule_date_pairs_and_monthly_series(self):
        ev = self.events()
        pairs = [(e["task"].rule_id, e["date"]) for e in ev]
        self.assertEqual(len(pairs), len(set(pairs)))
        alarms = [e["date"] for e in ev if e["task"].rule_id == "R-ALARM-001"]
        self.assertEqual(len(alarms), 13); self.assertEqual(alarms[1], self.dt.date(2026, 11, 29))

    def test_needs_info_is_one_event_not_a_series(self):
        self.assertEqual(sum(1 for e in self.events() if e["task"].rule_id == "R-AC-001"), 1)

    @classmethod
    def tearDownClass(cls):
        import shutil
        for f in HOUSES.glob("t-*"):
            try:
                shutil.rmtree(f) if f.is_dir() else f.unlink()
            except OSError:
                pass


class Checkpoint8(unittest.TestCase):
    """Drives the real HTTP server on a spare port against the synthetic sample."""
    @classmethod
    def setUpClass(cls):
        import threading, server as srv
        http.clear_fixtures(); http.set_offline(True)
        builder.build(samples.install("complete"), house_id="t-web", synthetic=True)
        http.set_offline(False); http.clear_fixtures()
        from http.server import ThreadingHTTPServer
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler)
        cls.port = cls.srv.server_address[1]
        cls.th = threading.Thread(target=cls.srv.serve_forever, daemon=True); cls.th.start()

    def get(self, path):
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return r.status, r.read().decode("utf-8")

    def post(self, path, data):
        import urllib.request, urllib.parse
        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=urllib.parse.urlencode(data).encode(), method="POST")
        try:
            return urllib.request.build_opener(NR).open(req).status
        except urllib.error.HTTPError as e_:
            return e_.code

    def test_pages_render_without_error(self):
        for path in ["/", "/house/t-web", "/house/t-web/plan", "/house/t-web/budget", "/house/t-web/history",
                     "/house/t-web/reports?kind=buy", "/house/t-web/reports?kind=calendar", "/house/t-web/fit?hours=1&dollars=50",
                     "/house/t-web/providers/R-WH-001", "/house/t-web/brief/R-CHIM-001", "/house/t-web/export.json", "/house/t-web/reminders.ics"]:
            st, body = self.get(path)
            self.assertEqual(st, 200, path); self.assertNotIn("Something went wrong", body, path)

    def test_actions_round_trip(self):
        self.assertEqual(self.post("/house/t-web/answer", {"field": "heating_fuel", "value": "gas", "reason": "t"}), 303)
        self.assertEqual(self.post("/house/t-web/done", {"task": "R-GFCI-001", "date": "2026-10-29", "notes": "", "cost": "", "contractor": ""}), 303)
        self.assertEqual(self.post("/house/t-web/dismiss", {"task": "R-AIR-001", "reason": "done"}), 303)
        p = Profile.load("t-web")
        self.assertEqual(p.value("heating_fuel"), "gas")
        self.assertTrue(any(c["rule_id"] == "R-GFCI-001" for c in p.completions))
        self.assertEqual(p.task_state["R-AIR-001"]["state"], "does_not_apply")
        st, body = self.get("/house/t-web/plan")
        self.assertIn("Set aside", body)

    def test_unknown_house_404(self):
        import urllib.request
        with self.assertRaises(urllib.error.HTTPError) as cm:
            urllib.request.urlopen(f"http://127.0.0.1:{self.port}/house/nope")
        self.assertEqual(cm.exception.code, 404)

    def test_snapshot_has_no_forms_and_is_labelled(self):
        import re, server as srv
        html = srv.web.plan_page(Profile.load("t-web"), snapshot=True)
        self.assertIn("read-only snapshot", html)
        html = re.sub(r"<form.*?</form>", "", html, flags=re.S)
        self.assertNotIn("<form", html)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()
        import shutil
        for f in HOUSES.glob("t-*"):
            try:
                shutil.rmtree(f) if f.is_dir() else f.unlink()
            except OSError:
                pass


class Redesign(unittest.TestCase):
    """One-page experience: scenarios 1–7 from the redesign brief, driven over HTTP."""
    @classmethod
    def setUpClass(cls):
        import threading, server as srv
        from http.server import ThreadingHTTPServer
        http.clear_fixtures(); http.set_offline(True)
        p = builder.build(samples.install("complete"), house_id="t-ux", synthetic=True)
        builder.apply_answer(p, "heating_fuel", "gas"); builder.apply_answer(p, "heating_type", "forced air")
        p.add_finding("electrical", "safety", "Open junction box", source_doc="inspection p.22"); p.save()
        http.set_offline(False); http.clear_fixtures()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), srv.Handler); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    def get(self, path):
        import urllib.request
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}{path}") as r:
            return r.read().decode("utf-8")

    def post(self, path, data):
        import urllib.request, urllib.parse
        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=urllib.parse.urlencode(data).encode(), method="POST")
        try:
            r = urllib.request.build_opener(NR).open(req); return r.status, r.headers.get("Location", "")
        except urllib.error.HTTPError as ex:
            return ex.code, ex.headers.get("Location", "")

    def test_1_2_next_action_and_why_on_first_screen(self):
        b = self.get("/house/t-ux")
        self.assertIn("Needs attention", b); self.assertIn("Do next", b)
        i = b.index("Do next"); first = b[i:i + 3000]
        self.assertIn("Open junction box", first)            # safety finding ranks first
        self.assertIn("Why it applies to this house", first)   # why is in the inline details

    def test_3_details_keep_place(self):
        b = self.get("/house/t-ux?open=R-WH-001")
        i = b.index('id="R-WH-001"')
        self.assertIn("<details open>", b[i:i + 4000])  # opened in place, same page

    def test_4_complete_postpone_feedback_and_undo(self):
        self.get("/house/t-ux")  # clear any flash from an earlier test
        st, loc = self.post("/house/t-ux/done", {"task": "R-GFCI-001", "back": "R-GFCI-001"})
        self.assertEqual(st, 303); self.assertTrue(loc.endswith("#R-GFCI-001"))
        b = self.get("/house/t-ux"); self.assertIn("Done: Test GFCI", b); self.assertIn('action="/house/t-ux/undo"', b)
        self.post("/house/t-ux/undo", {"task": "R-GFCI-001"})
        self.assertFalse(any(c["rule_id"] == "R-GFCI-001" for c in Profile.load("t-ux").completions))
        st, loc = self.post("/house/t-ux/snooze", {"task": "R-GUTTER-001", "back": "R-GUTTER-001", "days": "7"})
        self.assertEqual(Profile.load("t-ux").task_state["R-GUTTER-001"]["state"], "snoozed")
        self.assertIn("Postponed", self.get("/house/t-ux"))

    def test_5_provider_help_from_task(self):
        b = self.get("/house/t-ux?open=R-WH-001")
        self.assertIn("Who could do this (plumber)", b); self.assertIn("hiring checklist", b)
        self.assertNotIn("vetted", b.lower())

    def test_6_correct_a_house_detail_updates_plan(self):
        before = {t.rule_id: t.status for t in rules.evaluate(Profile.load("t-ux"))}
        st, loc = self.post("/house/t-ux/answer", {"field": "chimney_in_use", "value": "no", "next": "house"})
        self.assertTrue(loc.endswith("#house"))
        b = self.get("/house/t-ux"); self.assertIn("R-CHIM-001: applies → excluded", b)
        self.assertEqual(before["R-CHIM-001"], "applies")

    def test_7_missing_information_still_gives_next_step(self):
        http.clear_fixtures(); http.set_offline(True)
        builder.build(samples.install("missing"), house_id="t-ux-missing", synthetic=True)
        http.set_offline(False); http.clear_fixtures()
        b = self.get("/house/t-ux-missing")
        self.assertIn("Do next", b); self.assertIn("One answer would sharpen this plan", b)
        self.assertIn("unknown", b)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()
        import shutil
        for f in HOUSES.glob("t-*"):
            try:
                shutil.rmtree(f) if f.is_dir() else f.unlink()
            except OSError:
                pass



class Landing(Redesign):
    """Landing page, /owner, and Browse Homes as a prospective buyer's overview."""
    # reuse the HTTP harness only; the Redesign scenarios already run in their own class
    test_1_2_next_action_and_why_on_first_screen = test_3_details_keep_place = None
    test_4_complete_postpone_feedback_and_undo = test_5_provider_help_from_task = None
    test_6_correct_a_house_detail_updates_plan = test_7_missing_information_still_gives_next_step = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.made = []

    @classmethod
    def tearDownClass(cls):
        for hid in cls.made + ["browse-sample-complete", "browse-sample-missing"]:
            try:
                (HOUSES / f"{hid}.json").unlink(missing_ok=True)
            except OSError:  # a folder that forbids deletes; these records are synthetic
                pass

    def status(self, path):
        import urllib.request, urllib.error
        class NR(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        try:
            r = urllib.request.build_opener(NR).open(f"http://127.0.0.1:{self.port}{path}"); return r.status, ""
        except urllib.error.HTTPError as ex:
            return ex.code, ex.headers.get("Location", "")

    def example(self, name):
        st, loc = self.post("/sample", {"name": name, "mode": "browse"})
        self.assertEqual((st, loc), (303, f"/browse/browse-sample-{name}"))
        return self.get(loc)

    def test_landing_two_choices_and_routes(self):
        b = self.get("/")
        self.assertIn('href="/owner"', b); self.assertIn('href="/browse"', b)
        self.assertIn("prefers-reduced-motion", b); self.assertIn(":focus-visible", b)
        self.assertNotIn("<form", b)
        self.assertIn('action="/build"', self.get("/owner"))
        bb = self.get("/browse")
        self.assertIn('name="mode" value="browse"', bb); self.assertIn("list homes for sale", bb)

    def test_browse_empty_address_returns_to_browse(self):
        st, loc = self.post("/build", {"address": "", "mode": "browse"})
        self.assertEqual(st, 303); self.assertTrue(loc.startswith("/browse"))
        st, loc = self.post("/build", {"address": ""})
        self.assertTrue(loc.startswith("/owner"))

    def test_browse_has_no_homeowner_task_content(self):
        for name in ("complete", "missing"):
            b = self.example(name)
            low = b.split("</style>", 1)[1].lower()  # page content, not the stylesheet
            for gone in ("do next", "/done", "/snooze", "/dismiss", 'type="checkbox"', ".ics", "reminder", "calendar",
                         "overdue", "next three", "filter", "smoke", "alarm", "hvac", "furnace", "mark done"):
                self.assertNotIn(gone, low, f"{name}: {gone!r} should not appear in Browse Homes")
            for part in ('id="glance"', 'id="major"', 'id="ownership"', 'id="unknowns"'):
                self.assertIn(part, b)
            self.assertIn("Track it as my home", b)  # secondary transition, after the overview
            self.assertLess(b.index('id="unknowns"'), b.index("Track it as my home"))

    def test_complete_example_overview(self):
        b = self.example("complete")
        self.assertIn("A 1928 brick colonial with a full basement", b)
        self.assertIn("Possible sewer-line repair", b); self.assertIn("Needs assessment", b)
        # roof age is not inferred from the 1928 construction year
        major = b[b.index('id="major"'):b.index('id="ownership"')]
        self.assertNotIn("Roof replacement", major); self.assertIn("How old is the roof", b)
        self.assertIn("undermined by coal mining", b)
        self.assertIn("repair cost unknown unless the test fails", b)  # no invented repair price
        self.assertIn("<details", b)  # evidence opens in place

    def test_sparse_record_stays_unknown(self):
        b = self.example("missing")
        self.assertIn("Not recorded", b)
        self.assertIn('<dt>Built</dt><dd>Not recorded', b)
        self.assertIn("Slope, retaining-wall or drainage work", b)
        self.assertIn("2022-06-14", b)            # roof permit drives the roof question
        self.assertIn("Fair", b); self.assertNotIn("Broad repair", b)  # 'Fair' alone is not major work
        self.assertIn("Flood zone: not retrieved", b)

    def test_roof_planning_needs_an_established_age(self):
        from hk import buyer
        http.clear_fixtures(); http.set_offline(True)
        try:
            p = builder.build(samples.install("complete"), house_id="t-browse-roof", synthetic=True)
        finally:
            http.set_offline(False); http.clear_fixtures()
        self.made.append("t-browse-roof")
        self.assertFalse([m for m in buyer.major_work(p) if m["key"] == "roof"])
        builder.apply_answer(p, "roof_installed_year", 2004, reason="seller's roofing invoice")
        roof = [m for m in buyer.major_work(p) if m["key"] == "roof"]
        self.assertEqual(len(roof), 1); self.assertEqual(roof[0]["status"], "planning")
        self.assertIn("condition, not age", roof[0]["what"])

    def test_no_major_work_says_so(self):
        from hk import browse
        http.clear_fixtures(); http.set_offline(True)
        try:
            p = builder.build(samples.install("complete"), house_id="t-browse-none", synthetic=True)
        finally:
            http.set_offline(False); http.clear_fixtures()
        self.made.append("t-browse-none")
        p.overlays.pop("point_of_sale_sewer_rule", None)
        h = browse.browse_property(p, [])
        self.assertIn("doesn&rsquo;t establish any major project", h)
        self.assertIn("absence of records is not an absence of problems", h)

    def test_lookup_never_touches_or_shows_an_owner_record(self):
        from hk.evidence import slug
        addr = samples.SAMPLES["complete"]
        oid = slug(addr)
        http.clear_fixtures(); http.set_offline(True)
        try:
            p = builder.build(samples.install("complete"), house_id=oid, synthetic=True)
            builder.apply_answer(p, "stage", "owner")
            p.add_finding("roof", "major", "PRIVATE-FINDING-XYZ"); p.documents.append({"id": "d-1", "title": "PRIVATE-INVOICE-XYZ"}); p.save()
            self.made += [oid, "browse-" + oid]
            st, loc = self.post("/build", {"address": addr, "mode": "browse"})
        finally:
            http.set_offline(False); http.clear_fixtures()
        self.assertEqual(loc, "/browse/browse-" + oid)
        b = self.get(loc)
        self.assertNotIn("PRIVATE-", b)
        kept = Profile.load(oid)
        self.assertEqual(kept.value("stage"), "owner"); self.assertEqual(len(kept.findings), 1)
        self.assertNotIn(oid, [h for h in self.get("/browse").split('href="/browse/')[1:] if h.startswith(oid + '"')])
        # 'Track it as my home' on an address the owner already has goes to it; nothing is rebuilt
        st, loc = self.post("/build", {"address": addr})
        self.assertEqual(loc, f"/house/{oid}"); self.assertEqual(len(Profile.load(oid).findings), 1)

    def test_switching_and_redirects(self):
        self.example("complete"); b = self.example("missing")
        self.assertIn('href="/browse/browse-sample-complete"', b)
        self.assertIn('href="/browse/browse-sample-missing" aria-current="page"', b)
        self.assertEqual(self.status("/house/browse-sample-missing"), (303, "/browse/browse-sample-missing"))
        self.assertNotIn("browse-sample", self.get("/owner"))
        self.assertEqual(self.status("/browse/t-ux")[0], 404)   # owned houses aren't shown as browse pages

    def test_ambiguous_lookup_can_be_resolved(self):
        http.clear_fixtures(); http.set_offline(True)
        try:
            st, loc = self.post("/build", {"address": samples.install("ambiguous"), "mode": "browse"})
            hid = loc.rsplit("/", 1)[1]; self.made.append(hid)
            self.assertIn("matched more than one property", self.get(loc))
            st, loc2 = self.post(f"/browse/{hid}/choose", {"choose": "1"})
        finally:
            http.set_offline(False); http.clear_fixtures()
        self.assertEqual(loc2, loc)
        self.assertEqual(Profile.load(hid).value("stage"), "before_buy")

    def test_owner_page_keeps_task_management(self):
        b = self.get("/house/t-ux")
        self.assertIn("Do next", b); self.assertIn("/done", b)


class OwnershipScore(unittest.TestCase):
    """Ownership Score scenarios on SYNTHETIC fixtures (invented addresses, records and sales)."""
    def setUp(self):
        from hk import records, score
        self.score, self.records = score, records
        http.clear_fixtures(); http.set_offline(True)
        try:
            self.p = builder.build(samples.install("complete"), house_id="t-score", mode="offline-sample", synthetic=True)
            self.p.set(records.price_benchmark(self.p, score.config()["price"]))
            self.m = builder.build(samples.install("missing"), house_id="t-score-missing", mode="offline-sample", synthetic=True)
            self.m.set(records.price_benchmark(self.m, score.config()["price"]))
        finally:
            http.set_offline(False); http.clear_fixtures()
        self.p.correct("asking_price", 345000, source_id="user", reason="test")

    def tearDown(self):
        for hid in ("t-score", "t-score-missing"):
            try:
                (HOUSES / f"{hid}.json").unlink(missing_ok=True)
            except OSError:
                pass

    def comp(self, p, key):
        return next(c for c in self.score.compute(p)["components"] if c["key"] == key)

    def test_benchmark_from_valid_recent_similar_sales(self):
        b = self.p.get("price_benchmark").value
        self.assertEqual(b["n"], 8)                       # the 30-month-old sale and the $1 transfer are excluded
        self.assertEqual(b["scope"], "neighborhood"); self.assertTrue(b["era_filter"])
        self.assertNotIn("FAIRMARKET", json.dumps(b))     # tax assessment is never the benchmark

    def test_identical_inputs_identical_scores(self):
        a, b = self.score.compute(self.p), self.score.compute(self.p)
        self.assertEqual(a, b)
        self.assertEqual(a["overall"] % 5, 0)

    def test_higher_price_never_improves_price_component(self):
        last = 101
        for price in (250000, 300000, 345000, 380000, 420000, 480000, 600000):
            self.p.correct("asking_price", price, source_id="user", reason="test")
            s = self.comp(self.p, "price")["score"]
            self.assertLessEqual(s, last); last = s

    def test_cheaper_is_capped(self):
        self.p.correct("asking_price", 120000, source_id="user", reason="test")
        c = self.comp(self.p, "price")
        self.assertEqual(c["score"], 80)
        self.assertIn("often reflect condition", c["drivers"][0]["text"])

    def test_more_documented_work_never_improves_major(self):
        base = self.comp(self.p, "major")["score"]
        self.p.add_finding("roof", "major", "Shingles curling, granule loss; replacement advised", source_doc="SYNTHETIC inspection p.4")
        one = self.comp(self.p, "major")
        self.p.add_finding("foundation", "major", "Horizontal crack in north wall", source_doc="SYNTHETIC inspection p.9")
        two = self.comp(self.p, "major")["score"]
        self.assertLess(one["score"], base); self.assertLess(two, one["score"])
        self.assertTrue(any("roof findings increase major-work exposure" in d["text"] for d in one["drivers"]))
        # the same roof isn't counted twice (finding + age)
        self.assertFalse(any(d["text"].startswith("Roof age is unknown") for d in one["drivers"]))

    def test_unknown_roof_is_not_treated_like_a_documented_new_roof(self):
        unknown = self.comp(self.p, "major")["score"]
        self.p.correct("roof_installed_year", 2021, source_id="user", reason="SYNTHETIC roofing invoice")
        recent = self.comp(self.p, "major")["score"]
        self.p.correct("roof_installed_year", 2004, source_id="user", reason="SYNTHETIC roofing invoice")
        old = self.comp(self.p, "major")["score"]
        self.assertGreater(recent, unknown); self.assertLess(old, unknown)
        self.p.correct("year_built", 1999, source_id="user", reason="test")   # construction year never sets roof age
        self.p.correct("roof_installed_year", 2004, source_id="user", reason="unchanged")
        self.assertEqual(self.comp(self.p, "major")["score"], old)

    def test_missing_essential_data_withholds_overall(self):
        s = self.score.compute(self.m)
        self.assertIsNone(s["overall"])
        price = next(c for c in s["components"] if c["key"] == "price")
        self.assertFalse(price["available"]); self.assertEqual(price["status_text"], "Price assessment unavailable")
        self.assertTrue(all(c["available"] for c in s["components"] if c["key"] != "price"))   # shown independently
        self.assertTrue(any("comparable sales" in n for n in s["needed"]))
        self.m.correct("asking_price", 140000, source_id="user", reason="test")
        self.assertIsNone(self.score.compute(self.m)["overall"])           # a price alone can't stand in for a benchmark

    def test_unknown_is_not_best_case(self):
        mc = self.comp(self.m, "maintenance")
        self.assertTrue(any("Flood zone not retrieved" in a for a in mc["assumptions"]))
        self.assertTrue(any("Basement not recorded" in a for a in mc["assumptions"]))

    def test_completeness_does_not_change_score(self):
        before = self.score.compute(self.p)
        self.p.correct("roof_installed_year", 2004, source_id="user", reason="SYNTHETIC")
        after = self.score.compute(self.p)
        self.assertGreater(after["completeness"]["n_known"], before["completeness"]["n_known"])
        self.assertLessEqual(after["overall"], before["overall"])   # more information, worse roof: no completeness bonus

    def test_costs_counted_once(self):
        s = self.score.compute(self.p)
        texts = [d["text"] for c in s["components"] for d in c["drivers"]]
        self.assertEqual(len(texts), len(set(texts)))
        maint = " ".join(d["text"] for d in self.comp(self.p, "maintenance")["drivers"]).lower()
        major = " ".join(d["text"] for d in self.comp(self.p, "major")["drivers"]).lower()
        self.assertNotIn("sewer", maint); self.assertNotIn("insurance", major); self.assertNotIn("roof", maint)
        cfg = self.score.config()
        self.assertAlmostEqual(sum(cfg["weights"].values()), 1.0)

    def test_shared_exterior_helps_maintenance(self):
        base = self.comp(self.p, "maintenance")["score"]
        self.p.correct("hoa_exterior", "yes", source_id="user", reason="test")
        c = self.comp(self.p, "maintenance")
        self.assertGreater(c["score"], base)
        self.assertTrue(any("reduces the owner's direct upkeep" in d["text"] for d in c["drivers"]))


class ScoreOverHTTP(Landing):
    """The score inside the Browse page: inputs, corrections and explanations, over HTTP."""
    test_landing_two_choices_and_routes = test_browse_empty_address_returns_to_browse = None
    test_browse_has_no_homeowner_task_content = test_complete_example_overview = test_sparse_record_stays_unknown = None
    test_roof_planning_needs_an_established_age = test_no_major_work_says_so = None
    test_lookup_never_touches_or_shows_an_owner_record = test_switching_and_redirects = None
    test_ambiguous_lookup_can_be_resolved = test_owner_page_keeps_task_management = None

    def test_price_entry_corrects_and_updates_score_and_explanation(self):
        b = self.example("complete")
        self.assertIn("Score withheld", b); self.assertIn("Price assessment unavailable", b)
        self.assertIn('id="ask"', b)
        st, loc = self.post("/browse/browse-sample-complete/inputs", {"asking_price": "$345,000", "hoa_exterior": "unknown", "action": "update"})
        self.assertEqual(loc, "/browse/browse-sample-complete#score")
        b1 = self.get("/browse/browse-sample-complete")
        self.assertIn("Score updated", b1); self.assertIn("entered by you", b1)
        self.assertIn("at or slightly below the comparable-sales benchmark", b1)
        self.post("/browse/browse-sample-complete/inputs", {"asking_price": "450k", "hoa_exterior": "unknown", "action": "update"})
        b2 = self.get("/browse/browse-sample-complete")
        self.assertIn("above the comparable-sales benchmark", b2)
        self.assertNotIn("at or slightly below the comparable-sales benchmark", b2)
        self.assertIn("potential major item", b2)          # major concerns stay visible beside the score
        st, loc = self.post("/browse/browse-sample-complete/inputs", {"asking_price": "lots", "action": "update"})
        self.assertIn("read &#x27;lots&#x27; as a price", self.get("/browse/browse-sample-complete"))  # bad input explained, price kept
        self.post("/browse/browse-sample-complete/inputs", {"action": "clear", "hoa_exterior": "unknown"})
        self.assertIn("Score withheld", self.get("/browse/browse-sample-complete"))

    def test_score_panel_has_method_and_is_keyboard_reachable(self):
        b = self.example("missing")
        self.assertIn('id="score"', b); self.assertIn("How this score works", b)
        self.assertIn("Price assessment unavailable", b); self.assertIn("Needed to complete the score", b)
        self.assertIn('role="meter"', b); self.assertIn("Evidence: ", b)
        self.assertLess(b.index('id="score"'), b.index('id="glance"'))
