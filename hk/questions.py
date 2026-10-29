"""Confirmation flow: ask only what could change a recommendation.

The question list is derived from (a) rules whose status is needs_info/verification and
(b) a short, fixed set of high-value onboarding fields (section 4A of the brief), filtered
to those still unknown. Each question names the field it fills, the accepted answer form,
and which rule(s) it unblocks, so the user can see why it is being asked.
"""
from __future__ import annotations

from .evidence import Profile
from .rules import Task

# field -> (prompt, answer_hint, parser name)
ONBOARDING = [
    ("owner_confirms_match", "Is this the right parcel/address?", "yes / no", "bool"),
    ("stage", "Where are you in the process?", "under_contract / owner", "choice"),
    ("closing_date", "Closing date (or the date you took ownership)?", "YYYY-MM-DD", "date"),
    ("heating_fuel", "What fuels the heating system?", "gas / oil / propane / electric / heat pump", "choice"),
    ("heating_type", "What kind of heating system?", "forced air / boiler / heat pump / radiant", "choice"),
    ("ac_present", "Is there central air conditioning?", "yes / no", "bool"),
    ("water_heater_type", "What kind of water heater?", "tank / tankless", "choice"),
    ("furnace_installed_year", "About what year was the furnace or boiler installed?", "year or 'unknown'", "year"),
    ("water_heater_installed_year", "About what year was the water heater installed?", "year or 'unknown'", "year"),
    ("roof_installed_year", "What year was the roof last replaced?", "year or 'unknown'", "year"),
    ("sump_pump_present", "Is there a sump pump in the basement?", "yes / no / unknown", "bool"),
    ("radon_result_date", "Date of the most recent radon test, if any", "YYYY-MM-DD or 'none'", "date"),
    ("radon_result_pci_l", "Radon test result, if known", "number (pCi/L)", "number"),
    ("radon_mitigation_present", "Is there an existing radon mitigation system (fan + pipe)?", "yes / no", "bool"),
    ("chimney_in_use", "Is the chimney/fireplace used?", "yes / no", "bool"),
    ("dryer_present", "Is there a clothes dryer?", "yes / no", "bool"),
    ("exterior_hose_bibs", "Are there exterior hose faucets?", "yes / no", "bool"),
    ("gutters_present", "Does the house have gutters?", "yes / no", "bool"),
    ("wiring_type", "What does the inspection say about wiring?", "knob-and-tube / ungrounded / mixed / modern grounded / rewired", "choice"),
    ("plumbing_supply_material", "Supply pipe material?", "galvanized / copper / pex / cpvc / lead / mixed", "choice"),
    ("oldest_smoke_alarm_year", "Oldest smoke-alarm manufacture year?", "year or 'unknown'", "year"),
    ("wdi_inspection_date", "Date of a wood-destroying-insect inspection, if any", "YYYY-MM-DD or 'none'", "date"),
    ("hoa_or_shared", "Is there an HOA or any shared-responsibility items (party wall, shared drive)?", "yes / no", "bool"),
    ("known_problems", "Any known problems from the inspection or seller disclosure?", "short text", "text"),
]


DERIVED_FROM = {"water_heater_age_years": "water_heater_installed_year", "roof_age_years": "roof_installed_year",
                "furnace_age_years": "furnace_installed_year"}


def pending(p: Profile, tasks: list[Task]) -> list[dict]:
    unblocks: dict[str, list[str]] = {}
    for t in tasks:
        if t.status in ("needs_info", "verification"):
            for m in t.missing:
                base = m.split(".")[0]
                unblocks.setdefault(DERIVED_FROM.get(base, base), []).append(t.rule_id)
    out = []
    for name, prompt, hint, kind in ONBOARDING:
        if name == "owner_confirms_match":
            if p.match.get("ambiguous") or p.match.get("owner_confirmed"):
                continue
        elif not p.get(name).is_unknown:
            continue
        out.append({"field": name, "question": prompt, "answer": hint, "type": kind,
                    "unblocks": unblocks.get(name, []),
                    "matters_because": _why(name)})
    # rules that need something not in the onboarding list
    for fld, ids in unblocks.items():
        if fld not in [q["field"] for q in out] and p.get(fld).is_unknown and fld not in [n for n, *_ in ONBOARDING]:
            out.append({"field": fld, "question": f"Value for {fld}?", "answer": "", "type": "text",
                        "unblocks": ids, "matters_because": "a rule needs it"})
    # ask what unblocks something first
    out.sort(key=lambda q: (0 if q["unblocks"] else 1))
    return out


def _why(name: str) -> str:
    return {
        'owner_confirms_match': 'everything else depends on having the right parcel',
        'stage': "while you're under contract there are deadlines; after closing there aren't",
        'closing_date': 'sets the dates for your first 90 days',
        'heating_fuel': "gas and oil systems need a yearly safety service; electric ones don't",
        'heating_type': 'boilers and forced-air systems need different checks',
        'ac_present': 'adds a spring AC check',
        'water_heater_type': 'tankless units skip the flushing and anode checks',
        'furnace_installed_year': 'tells us when to start planning for a replacement',
        'water_heater_installed_year': 'tells us when to start planning for a replacement',
        'roof_installed_year': 'the biggest cost to plan for; unknown keeps it a guess',
        'sump_pump_present': "adds a quarterly test; without one we'll ask you to check the basement",
        'radon_result_date': "a test within two years means you don't need another yet",
        'radon_result_pci_l': '4 or higher is the level EPA says to fix',
        'radon_mitigation_present': 'an existing system needs a monthly glance, not a new quote',
        'chimney_in_use': "a sealed or unused chimney doesn't need yearly inspection",
        'dryer_present': 'adds the dryer-vent fire check',
        'exterior_hose_bibs': 'adds the fall reminder to drain them before the first freeze',
        'gutters_present': 'no gutters means no gutter cleaning',
        'wiring_type': 'modern grounded wiring removes the electrical check',
        'plumbing_supply_material': 'copper or PEX removes the pipe check; lead becomes a health item',
        'oldest_smoke_alarm_year': 'alarms over 10 years old get replaced',
        'wdi_inspection_date': 'a termite report on file removes that check',
        'hoa_or_shared': 'moves shared items off your list',
        'known_problems': 'problems the inspector found come first',
    }.get(name, "")


def parse_answer(kind: str, raw: str):
    s = raw.strip().lower()
    if s in ("", "unknown", "?", "none", "n/a", "dont know", "don't know"):
        return None
    if kind == "bool":
        return s in ("y", "yes", "true", "1")
    if kind == "year":
        y = int(s)
        if not 1700 <= y <= 2100:
            raise ValueError("year out of range")
        return y
    if kind == "number":
        return float(s)
    if kind == "date":
        return raw.strip()
    return raw.strip()
