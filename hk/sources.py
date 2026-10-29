"""Source registry: data/sources.json (built by audit/build_sources_json.py)."""
from __future__ import annotations

import json
from functools import lru_cache

from . import DATA


@lru_cache(maxsize=1)
def registry() -> dict:
    doc = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    return {s["id"]: s for s in doc["sources"]}


def get(source_id: str) -> dict:
    reg = registry()
    if source_id not in reg:
        raise KeyError(f"unknown source id {source_id!r}; add it to data/sources.json")
    return reg[source_id]


def citation(source_id: str, ref: str = "") -> str:
    s = get(source_id)
    base = f"{s['publisher']} — {s['name']} ({s['url']})"
    return base + (f" — {ref}" if ref else "")
