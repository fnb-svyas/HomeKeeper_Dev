"""HomeKeeper prototype — standard-library-only package.

Modules:
  http        - cached GET/POST with identifying User-Agent and offline mode
  sources     - source registry (data/sources.json)
  evidence    - Field / Profile model with provenance and history
  geocode     - address -> candidates (county geocoder; Census fallback)
  records     - WPRDC assessments, City of Pittsburgh permits
  overlays    - radon, flood, mine subsidence, landslide, soils, climate normals
  municipal   - hand-curated municipal point-of-sale rules
  builder     - orchestrates address -> profile
  questions   - confirmation questions that could change recommendations
  rules       - minimal data-driven rule engine (seed; expanded in Checkpoint 3)
  doctor      - live endpoint checks to run on the user's machine
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
HOUSES = ROOT / "houses"
CACHE = ROOT / "cache"
VERSION = "0.9.5-score"
