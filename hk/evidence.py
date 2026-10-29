"""Evidence model: every profile value carries its provenance and keeps its history.

Evidence types (section 4B of the brief):
  public_record | owner_reported | professional_finding | manufacturer |
  regional_exposure | inference | unknown

Verification statuses:
  unverified      - taken from a source, not yet confirmed by the owner
  owner_confirmed - the owner said "yes, that's right"
  owner_corrected - the owner replaced the value (previous value kept in history)
  documented      - backed by a document in the house record (invoice, report, label photo)
  conflicting     - two sources disagree; both kept in `conflicts`
  unknown         - nobody knows yet; this is a real state, not False

A correction never erases provenance: the old Field is appended to `history`.
Unknown fields are stored explicitly so that rules can require them and ask.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from . import HOUSES

EVIDENCE_TYPES = ("public_record", "owner_reported", "professional_finding", "manufacturer",
                  "regional_exposure", "inference", "unknown")
STATUSES = ("unverified", "owner_confirmed", "owner_corrected", "documented", "conflicting", "unknown")


def today() -> str:
    return time.strftime("%Y-%m-%d")


@dataclass
class Field:
    name: str
    value: Any = None
    units: Optional[str] = None
    source_id: Optional[str] = None       # id in data/sources.json, or "owner", "inspection:<doc id>"
    source_ref: str = ""                  # exact field/record/page the value came from
    observed_date: Optional[str] = None   # when the fact was true/observed, if known
    retrieved_date: Optional[str] = None  # when we fetched/entered it
    evidence_type: str = "unknown"
    verification_status: str = "unknown"
    limitations: str = ""
    conflicts: list = field(default_factory=list)   # other Fields (as dicts) that disagree
    history: list = field(default_factory=list)     # previous versions (as dicts), newest last
    note: str = ""

    def __post_init__(self):
        assert self.evidence_type in EVIDENCE_TYPES, self.evidence_type
        assert self.verification_status in STATUSES, self.verification_status
        if self.value is None:
            self.evidence_type = "unknown"
            self.verification_status = "unknown"

    @property
    def is_unknown(self) -> bool:
        return self.value is None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Field":
        return Field(**d)

    def supersede(self, new: "Field") -> "Field":
        """Return `new` with this field's full record pushed onto history."""
        new.history = list(self.history) + [self._snapshot()]
        return new

    def _snapshot(self) -> dict:
        d = self.to_dict()
        d.pop("history", None)
        return d


def unknown(name: str, limitations: str = "", note: str = "") -> Field:
    return Field(name=name, value=None, limitations=limitations, note=note)


@dataclass
class Profile:
    house_id: str
    address_input: str
    created: str = field(default_factory=today)
    updated: str = field(default_factory=today)
    mode: str = "live"                      # live | offline-sample
    synthetic: bool = False                 # True for demo fixtures (never real data)
    match: dict = field(default_factory=dict)   # geocode/parcel match record incl. candidates
    fields: dict = field(default_factory=dict)  # name -> Field dict
    overlays: dict = field(default_factory=dict)  # name -> Field dict (regional exposure)
    equipment: list = field(default_factory=list)   # identified equipment (see add_equipment)
    findings: list = field(default_factory=list)    # documented findings (inspection report etc.)
    responsibilities: dict = field(default_factory=dict)  # component -> party ("HOA", "landlord", ...)
    estimates: list = field(default_factory=list)       # cost estimates (see hk/budget.py)
    reserves: dict = field(default_factory=dict)        # component -> reserve scenario
    documents: list = field(default_factory=list)       # document references (see hk/actions.py)
    completions: list = field(default_factory=list)     # completed work (see hk/actions.py)
    task_state: dict = field(default_factory=dict)      # rule_id -> snoozed / does_not_apply
    log: list = field(default_factory=list)   # free-text event log (what changed, when, why)

    # ---- field access -------------------------------------------------------
    def get(self, name: str) -> Field:
        d = self.fields.get(name) or self.overlays.get(name)
        return Field.from_dict(d) if d else unknown(name)

    def value(self, name: str, default=None):
        f = self.get(name)
        return default if f.is_unknown else f.value

    def set(self, f: Field, *, overlay: bool = False, reason: str = "") -> None:
        store = self.overlays if overlay else self.fields
        f.retrieved_date = f.retrieved_date or today()
        old = store.get(f.name)
        if old:
            old_f = Field.from_dict(old)
            if old_f.value == f.value and old_f.source_id == f.source_id:
                return  # nothing changed
            f = old_f.supersede(f)
        store[f.name] = f.to_dict()
        self.updated = today()
        self.log.append({"date": today(), "field": f.name, "value": f.value,
                         "source": f.source_id, "status": f.verification_status, "reason": reason})

    def correct(self, name: str, value, *, source_id: str = "owner", reason: str = "",
                observed_date: Optional[str] = None, units: Optional[str] = None,
                evidence_type: str = "owner_reported", status: str = "owner_corrected") -> Field:
        """Owner correction: keep provenance, record reason. Returns the new Field."""
        old = self.get(name)
        # Any public-record value that disagrees is retained as a conflict, not deleted.
        conflicts = []
        if not old.is_unknown and old.evidence_type == "public_record" and old.value != value:
            conflicts.append(old._snapshot())
        f = Field(name=name, value=value, units=units or old.units, source_id=source_id,
                  source_ref=f"owner entry on {today()}", observed_date=observed_date,
                  evidence_type=evidence_type, verification_status=status,
                  conflicts=conflicts, note=reason)
        self.set(f, overlay=(name in self.overlays), reason=reason or "owner correction")
        return f

    def confirm(self, name: str) -> None:
        f = self.get(name)
        if f.is_unknown:
            return
        f.verification_status = "owner_confirmed"
        self.set(f, overlay=(name in self.overlays), reason="owner confirmed")

    # ---- equipment / findings / responsibilities ----------------------------
    def add_equipment(self, component: str, *, make: str = "", model: str = "", installed_year=None,
                      manual_source_id: Optional[str] = None, source_id: str = "owner",
                      evidence_type: str = "owner_reported", observed_date: Optional[str] = None,
                      note: str = "") -> dict:
        """Record a piece of equipment. A replacement of the same component retires the old entry
        (kept with status 'replaced') so history is preserved and age-based rules reset."""
        eid = f"eq-{len(self.equipment)+1:03d}"
        for e in self.equipment:
            if e["component"] == component and e.get("status") == "installed":
                e["status"] = "replaced"
                e["replaced_on"] = today()
                self.log.append({"date": today(), "event": "equipment replaced", "equipment": e["id"], "by": eid})
        entry = {"id": eid, "component": component, "make": make, "model": model, "installed_year": installed_year,
                 "manual_source_id": manual_source_id, "source_id": source_id, "evidence_type": evidence_type,
                 "verification_status": "documented" if evidence_type in ("professional_finding", "manufacturer") else "owner_confirmed",
                 "observed_date": observed_date, "retrieved_date": today(), "status": "installed",
                 "last_service_date": None, "warranty": {}, "note": note}
        self.equipment.append(entry)
        self.log.append({"date": today(), "event": "equipment added", "equipment": eid, "component": component,
                         "installed_year": installed_year})
        self.updated = today()
        return entry

    def installed(self, component: str) -> Optional[dict]:
        for e in reversed(self.equipment):
            if e["component"] == component and e.get("status") == "installed":
                return e
        return None

    def add_finding(self, component: str, severity: str, description: str, *, recommendation: str = "",
                    source_doc: str = "inspection report", observed_date: Optional[str] = None,
                    location: str = "") -> dict:
        assert severity in ("safety", "major", "minor", "info"), severity
        fid = f"f-{len(self.findings)+1:03d}"
        entry = {"id": fid, "component": component, "severity": severity, "description": description,
                 "recommendation": recommendation, "location": location, "source_doc": source_doc,
                 "observed_date": observed_date, "recorded": today(), "evidence_type": "professional_finding",
                 "status": "open"}
        self.findings.append(entry)
        self.log.append({"date": today(), "event": "finding added", "finding": fid, "component": component, "severity": severity})
        self.updated = today()
        return entry

    def set_responsibility(self, component: str, party: Optional[str], reason: str = "") -> None:
        if party:
            self.responsibilities[component] = party
        else:
            self.responsibilities.pop(component, None)
        self.log.append({"date": today(), "event": "responsibility", "component": component, "party": party, "reason": reason})
        self.updated = today()

    # ---- persistence --------------------------------------------------------
    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Profile":
        return Profile(**d)

    def path(self):
        HOUSES.mkdir(parents=True, exist_ok=True)
        return HOUSES / f"{self.house_id}.json"

    def save(self) -> None:
        self.path().write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @staticmethod
    def load(house_id: str) -> "Profile":
        p = HOUSES / f"{house_id}.json"
        return Profile.from_dict(json.loads(p.read_text(encoding="utf-8")))

    @staticmethod
    def list_ids() -> list:
        HOUSES.mkdir(parents=True, exist_ok=True)
        return sorted(p.stem for p in HOUSES.glob("*.json"))


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:60]
