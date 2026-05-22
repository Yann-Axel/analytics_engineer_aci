"""
Cross-layer data quality validation.

dbt tests check column-level invariants (not_null, unique, accepted_values,
relationships). This script checks SYSTEM-level invariants:

  - revenue totals are consistent across staging → marts → semantic
  - business rules hold (margin within plausible range, classes well-formed)
  - the unstructured signal actually correlates with operational signal
    (the regeneration we just did was meant to fix exactly this)
  - reference-date logic produces stable values

Each check is a function returning (passed, message). The runner prints a
report and exits non-zero on any failure.

Run after `dbt run` (from inside dbt_project/).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent))
from aci_config import DB_PATH, REFERENCE_DATE


CheckResult = tuple[bool, str]
Check = Callable[[duckdb.DuckDBPyConnection], CheckResult]


# ── Cross-layer revenue consistency ───────────────────────────────────────────
def check_revenue_staging_to_marts(con) -> CheckResult:
    raw = con.execute("SELECT SUM(ticket_price_usd + ancillary_revenue_usd) FROM stg_bookings").fetchone()[0]
    fb  = con.execute("SELECT SUM(total_revenue_usd) FROM fact_booking").fetchone()[0]
    if raw is None or fb is None or abs(raw - fb) > 1:
        return False, f"stg_bookings revenue ${raw:,.0f} != fact_booking revenue ${fb:,.0f}"
    return True, f"stg_bookings == fact_booking == ${raw:,.0f}"


def check_revenue_marts_to_semantic(con) -> CheckResult:
    ff  = con.execute("SELECT SUM(total_revenue_usd) FROM fact_flight").fetchone()[0]
    srp = con.execute("SELECT SUM(total_revenue_usd) FROM sem_route_performance").fetchone()[0]
    if ff is None or srp is None or abs(ff - srp) > 1:
        return False, f"fact_flight revenue ${ff:,.0f} != sem_route_performance ${srp:,.0f}"
    return True, f"fact_flight == sem_route_performance == ${ff:,.0f}"


def check_revenue_marts_internal(con) -> CheckResult:
    fb = con.execute("SELECT SUM(total_revenue_usd) FROM fact_booking").fetchone()[0]
    ff = con.execute("SELECT SUM(total_revenue_usd) FROM fact_flight").fetchone()[0]
    if fb is None or ff is None or abs(fb - ff) > 1:
        return False, f"fact_booking ${fb:,.0f} != fact_flight ${ff:,.0f}"
    return True, "fact_booking ≅ fact_flight (bookings sum up to flight totals)"


# ── Business rules ────────────────────────────────────────────────────────────
def check_margin_range(con) -> CheckResult:
    bad = con.execute("""
        SELECT COUNT(*) FROM sem_route_performance
        WHERE margin_pct < -100 OR margin_pct > 100
    """).fetchone()[0]
    if bad > 0:
        return False, f"{bad} routes with implausible margin_pct"
    return True, "all margin_pct within ±100%"


def check_load_factor_range(con) -> CheckResult:
    bad = con.execute("""
        SELECT COUNT(*) FROM sem_route_performance
        WHERE avg_load_factor_pct < 0 OR avg_load_factor_pct > 100
    """).fetchone()[0]
    if bad > 0:
        return False, f"{bad} routes with load factor outside 0-100"
    return True, "all load_factor_pct within 0-100"


def check_ontology_coverage(con) -> CheckResult:
    n_routes = con.execute("SELECT COUNT(*) FROM dim_route").fetchone()[0]
    n_classified = con.execute("SELECT COUNT(*) FROM ont_route_classification").fetchone()[0]
    if n_classified != n_routes:
        return False, f"{n_classified}/{n_routes} routes classified"
    return True, f"all {n_routes} routes classified"


def check_customer_coverage(con) -> CheckResult:
    n_c = con.execute("SELECT COUNT(*) FROM dim_customer").fetchone()[0]
    n_cls = con.execute("SELECT COUNT(*) FROM ont_customer_classification").fetchone()[0]
    if n_cls != n_c:
        return False, f"{n_cls}/{n_c} customers classified"
    return True, f"all {n_c} customers classified"


def check_strategic_growth_exists(con) -> CheckResult:
    n = con.execute(
        "SELECT COUNT(*) FROM ont_route_classification WHERE route_class = 'Strategic Growth'"
    ).fetchone()[0]
    if n == 0:
        return False, "No Strategic Growth route — ontology may be miscalibrated"
    return True, f"{n} Strategic Growth route(s) identified"


def check_at_risk_bounds(con) -> CheckResult:
    n = con.execute(
        "SELECT COUNT(*) FROM ont_customer_classification WHERE customer_class = 'High-Value At-Risk'"
    ).fetchone()[0]
    # Business sanity: 1 to 60 out of 300 customers (0.3% to 20%).
    if not (1 <= n <= 60):
        return False, f"{n} High-Value At-Risk customers — outside expected 1-60 range"
    return True, f"{n} High-Value At-Risk customers (within plausible range)"


# ── Reference date invariants ─────────────────────────────────────────────────
def check_reference_date_freeze(con) -> CheckResult:
    """tenure_months should be stable; sample one customer and check it equals
    months_between(signup_date, REFERENCE_DATE)."""
    row = con.execute("""
        SELECT signup_date, tenure_months
        FROM stg_customers WHERE signup_date IS NOT NULL
        ORDER BY customer_id LIMIT 1
    """).fetchone()
    if not row:
        return False, "No customers found"
    signup, tenure = row
    # Compute expected via DuckDB to avoid Python date math drift.
    expected = con.execute(
        "SELECT date_diff('month', ?::date, ?::date)", [signup, REFERENCE_DATE]
    ).fetchone()[0]
    if tenure != expected:
        return False, f"tenure_months drift: stored {tenure} vs expected {expected}"
    return True, f"tenure_months anchored to {REFERENCE_DATE} (sample = {tenure})"


# ── Unstructured ↔ structured correlation ─────────────────────────────────────
def check_ticket_route_correlation(con) -> CheckResult:
    """Routes with worse ops (delay + cancel) should attract more tickets.
    We expect a positive Spearman-like rank correlation. Implemented as a
    Pearson on rank-encoded values via DuckDB to keep deps light."""
    rows = con.execute("""
        WITH route_summary AS (
            SELECT route_id,
                   delay_rate_pct + cancellation_rate_pct AS stress,
                   support_ticket_count                   AS tickets
            FROM sem_route_performance
        ),
        ranked AS (
            SELECT
                rank() OVER (ORDER BY stress)  AS r_stress,
                rank() OVER (ORDER BY tickets) AS r_tickets
            FROM route_summary
        )
        SELECT corr(r_stress, r_tickets) FROM ranked
    """).fetchone()
    corr = rows[0] if rows else 0
    if corr is None or corr < 0.3:
        return False, f"Ticket counts not correlated with operational stress (Spearman ≈ {corr})"
    return True, f"Tickets correlate with ops stress (Spearman ≈ {corr:.2f})"


def check_reviews_per_route(con) -> CheckResult:
    """Every route should have reviews — otherwise NPS at the route grain is null."""
    bad = con.execute("""
        SELECT COUNT(*) FROM sem_route_performance
        WHERE total_reviews IS NULL OR total_reviews = 0
    """).fetchone()[0]
    if bad > 0:
        return False, f"{bad} route(s) have no reviews"
    return True, "every route has reviews"


# ── Runner ────────────────────────────────────────────────────────────────────
CHECKS: list[tuple[str, Check]] = [
    ("Revenue: staging → marts",        check_revenue_staging_to_marts),
    ("Revenue: fact_booking == fact_flight", check_revenue_marts_internal),
    ("Revenue: marts → semantic",       check_revenue_marts_to_semantic),
    ("Margin within plausible range",   check_margin_range),
    ("Load factor within 0-100",        check_load_factor_range),
    ("Route ontology coverage",         check_ontology_coverage),
    ("Customer ontology coverage",      check_customer_coverage),
    ("At least one Strategic Growth",   check_strategic_growth_exists),
    ("High-Value At-Risk bounds",       check_at_risk_bounds),
    ("Reference date freeze",           check_reference_date_freeze),
    ("Tickets ↔ ops correlation",       check_ticket_route_correlation),
    ("Every route has reviews",         check_reviews_per_route),
]


def main() -> int:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    print("=== DATA QUALITY VALIDATION ===\n")
    passed = failed = 0
    failures: list[str] = []
    for name, check in CHECKS:
        ok, msg = check(con)
        marker = "✓" if ok else "✗"
        print(f"  {marker} {name:<42} {msg}")
        if ok:
            passed += 1
        else:
            failed += 1
            failures.append(f"{name}: {msg}")
    con.close()
    print(f"\n{passed}/{len(CHECKS)} checks passed" + (f" — {failed} failures" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
