"""
Air Côte d'Ivoire — Project-Wide Python Configuration

dbt_project.yml is the **single source of truth** for analytical constants
(reference_date, value tier thresholds). This module reads those values at
import time so Python scripts and dbt always see the same numbers.

REFERENCE_DATE is the analytical "as-of" date. It is FROZEN to one day after
the last operational record so date-based KPIs (days_since_last_booking,
tenure_months, dormant flags) remain stable regardless of when the pipeline
runs. Using CURRENT_DATE here would silently degrade the data over time.

To change a value, edit dbt_project.yml — never duplicate it here.
"""
from __future__ import annotations

from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "data" / "aci.duckdb"
DBT_PROJECT_FILE = PROJECT_ROOT / "dbt_project" / "dbt_project.yml"

with DBT_PROJECT_FILE.open(encoding="utf-8") as _f:
    _dbt_vars: dict = yaml.safe_load(_f).get("vars", {})

REFERENCE_DATE: str = _dbt_vars["reference_date"]
VALUE_TIER_HIGH_THRESHOLD: int = _dbt_vars["value_tier_high_threshold"]
VALUE_TIER_MID_THRESHOLD: int = _dbt_vars["value_tier_mid_threshold"]

DATA_RANGE_START = "2025-01-01"
DATA_RANGE_END = "2025-01-30"

RANDOM_SEED = 42

FUEL_PRICE_USD_PER_KG = 0.85
CREW_COST_USD_PER_BLOCK_HOUR = 350.0
AIRPORT_FEE_FIXED_USD = 400.0
AIRPORT_FEE_PER_KM = 0.04
