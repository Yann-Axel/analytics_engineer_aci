"""
Load the Air Cote d'Ivoire starter Excel dataset into DuckDB and export CSVs.

The Excel source lives in `data/source/` so the file ships with the repo and
can be loaded identically from a host venv or a Docker container. If the file
is missing locally, fall back to the parent-of-project location (used during
initial scaffolding).
"""
import duckdb
import openpyxl
import csv
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

RAW_EXCEL_CANDIDATES = [
    PROJECT_ROOT / "data" / "source" / "air_cote_divoire_starter_dataset.xlsx",
    PROJECT_ROOT.parent / "air_cote_divoire_starter_dataset.xlsx",
]
RAW_EXCEL = next((p for p in RAW_EXCEL_CANDIDATES if p.exists()), None)
if RAW_EXCEL is None:
    print(
        "ERROR: source Excel not found in either:\n  - "
        + "\n  - ".join(str(p) for p in RAW_EXCEL_CANDIDATES),
        file=sys.stderr,
    )
    sys.exit(1)

RAW_DIR = PROJECT_ROOT / "data" / "raw"
DB_PATH = PROJECT_ROOT / "data" / "aci.duckdb"

SHEETS = ["Airports", "Routes", "Customers", "Flights", "Bookings"]


def export_sheet_to_csv(wb, sheet_name: str, out_path: Path):
    ws = wb[sheet_name]
    rows = list(ws.iter_rows(values_only=True))
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow([str(v) if v is not None else "" for v in row])
    print(f"  Exported {sheet_name} -> {out_path.name} ({len(rows)-1} rows)")


def main():
    print("Loading raw Excel data...")
    wb = openpyxl.load_workbook(str(RAW_EXCEL), read_only=True, data_only=True)

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    for sheet in SHEETS:
        export_sheet_to_csv(wb, sheet, RAW_DIR / f"{sheet.lower()}.csv")

    print("\nLoading into DuckDB...")
    con = duckdb.connect(str(DB_PATH))

    for sheet in SHEETS:
        csv_path = RAW_DIR / f"{sheet.lower()}.csv"
        table = f"raw_{sheet.lower()}"
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"""
            CREATE TABLE {table} AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true)
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    con.close()
    print("\nDone. DuckDB at:", DB_PATH)


if __name__ == "__main__":
    main()
