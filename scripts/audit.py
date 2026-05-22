"""Full audit of the project against the challenge brief."""
import duckdb, os
from pathlib import Path

BASE = Path(__file__).parent.parent
DB = BASE / "data" / "aci.duckdb"
con = duckdb.connect(str(DB), read_only=True)

print("=" * 60)
print("FULL PROJECT AUDIT — Air Côte d'Ivoire Challenge")
print("=" * 60)

# 1. DuckDB tables
print("\n--- DuckDB Tables ---")
tables = con.execute(
    "SELECT table_name, table_type FROM information_schema.tables "
    "WHERE table_schema = 'main' ORDER BY table_name"
).df()
for _, r in tables.iterrows():
    try:
        n = con.execute(f"SELECT COUNT(*) FROM {r.table_name}").fetchone()[0]
        print(f"  {r.table_type:<6} {r.table_name:<42} {n:>7,} rows")
    except Exception as e:
        print(f"  ERROR {r.table_name}: {e}")

# 2. File inventory
print("\n--- Project Files ---")
for root, dirs, files in os.walk(str(BASE)):
    dirs[:] = [d for d in dirs if d not in ['target', '__pycache__', '.git', 'dbt_packages']]
    for f in sorted(files):
        if f.endswith(('.py', '.sql', '.yml', '.yaml', '.md', '.json')):
            rel = os.path.relpath(os.path.join(root, f), str(BASE))
            size = os.path.getsize(os.path.join(root, f))
            print(f"  {rel:<55} {size:>6} bytes")

# 3. KPI coverage check
print("\n--- KPI Coverage Check (sem_route_performance columns) ---")
cols = con.execute("DESCRIBE sem_route_performance").df()
for c in cols['column_name']:
    print(f"  {c}")

# 4. Ontology classes
print("\n--- Route Ontology Classes ---")
rc = con.execute(
    "SELECT route_class, COUNT(*) as n, "
    "ROUND(AVG(margin_pct),1) as avg_margin, "
    "ROUND(AVG(delay_rate_pct),1) as avg_delay "
    "FROM ont_route_classification GROUP BY route_class ORDER BY n DESC"
).df()
print(rc.to_string(index=False))

print("\n--- Customer Ontology Classes ---")
cc = con.execute(
    "SELECT customer_class, COUNT(*) as n, "
    "ROUND(AVG(total_revenue_usd),0) as avg_rev "
    "FROM ont_customer_classification GROUP BY customer_class ORDER BY n DESC"
).df()
print(cc.to_string(index=False))

# 5. Unstructured data check
print("\n--- Unstructured Data (Reviews + Tickets) ---")
rev_sentiments = con.execute(
    "SELECT sentiment, COUNT(*) as n FROM stg_reviews GROUP BY sentiment"
).df()
print("Reviews:", rev_sentiments.to_string(index=False))
tkt_cats = con.execute(
    "SELECT category, COUNT(*) as n FROM stg_support_tickets GROUP BY category ORDER BY n DESC"
).df()
print("Tickets:", tkt_cats.to_string(index=False))

# 6. MCP tools check
print("\n--- MCP Server Tools ---")
import ast
server_src = (BASE / "mcp_server" / "server.py").read_text()
tree = ast.parse(server_src)
tools = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and not n.name.startswith('_')]
for t in tools:
    print(f"  @mcp.tool: {t}")

# 7. Dashboard pages check
print("\n--- Dashboard Pages ---")
dash_src = (BASE / "dashboard" / "app.py").read_text()
pages = [line.strip().strip('"') for line in dash_src.split('\n')
         if 'elif page ==' in line or 'if page ==' in line]
for p in pages:
    p_clean = p.replace('elif page == ', '').replace('if page == ', '').strip('"').strip("'").strip(':')
    print(f"  Page: {p_clean}")

# 8. Docs check
print("\n--- Documentation Files ---")
for doc in sorted((BASE / "docs").glob("*.md")):
    lines = len(doc.read_text().splitlines())
    print(f"  {doc.name}: {lines} lines")
readme_lines = len((BASE / "README.md").read_text().splitlines())
print(f"  README.md: {readme_lines} lines")

con.close()
print("\n" + "=" * 60)
print("AUDIT COMPLETE")
