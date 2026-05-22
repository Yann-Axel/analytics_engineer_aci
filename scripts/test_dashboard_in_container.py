"""Smoke test the dashboard data layer from inside the dashboard container.

Verifies every query the four pages issue, plus the logo asset path. Not part
of the public flow — run via:

    docker exec aci-dashboard python /app/scripts/test_dashboard_in_container.py
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb

DB_PATH = "/app/data/aci.duckdb"
LOGO_PATH = "/app/dashboard/assets/aci_logo.jpg"


def main() -> int:
    con = duckdb.connect(DB_PATH, read_only=True)

    checks = [
        ("Page 1 routes",         "SELECT COUNT(*) FROM sem_route_performance"),
        ("Page 1 weekly",         "SELECT COUNT(*) FROM sem_weekly_kpis"),
        ("Page 1 classification", "SELECT COUNT(*) FROM ont_route_classification"),
        ("Page 2 customers",      "SELECT COUNT(*) FROM ont_customer_classification"),
        ("Page 2 segments",       "SELECT COUNT(*) FROM sem_customer_segments"),
        ("Page 2 reviews",        "SELECT COUNT(*) FROM stg_reviews"),
        ("Page 2 tickets",        "SELECT COUNT(*) FROM stg_support_tickets"),
        ("Page 3 bookings",       "SELECT COUNT(*) FROM fact_booking"),
        ("Page 4 ontology rts",   "SELECT COUNT(*) FROM ont_route_classification"),
        ("Page 4 ontology cust",  "SELECT COUNT(*) FROM ont_customer_classification"),
    ]

    print(f"{'Query':<28} {'Rows':>10}  Status")
    failed = 0
    for label, sql in checks:
        try:
            n = con.execute(sql).fetchone()[0]
            print(f"  {label:<26} {n:>10,}  OK")
        except Exception as exc:
            print(f"  {label:<26} {'-':>10}  FAIL: {exc}")
            failed += 1
    con.close()

    print()
    if Path(LOGO_PATH).exists():
        size = os.path.getsize(LOGO_PATH)
        print(f"Logo  {LOGO_PATH}  OK  ({size:,} bytes)")
    else:
        print(f"Logo  {LOGO_PATH}  MISSING")
        failed += 1

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
