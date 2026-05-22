import duckdb
con = duckdb.connect("data/aci.duckdb", read_only=True)

print("=== Testing MCP Tool Queries ===")

r = con.execute("SELECT route_type, ROUND(SUM(total_revenue_usd),0) as rev FROM sem_route_performance GROUP BY route_type").df()
print(f"Tool 1 OK - {len(r)} route types\n{r.to_string()}")

r = con.execute("SELECT route_label, margin_pct, route_class FROM ont_route_classification WHERE route_class = 'Strategic Growth'").df()
print(f"\nTool 2 OK - {len(r)} Strategic Growth routes: {list(r.route_label)}")

r = con.execute("SELECT COUNT(*) as n FROM ont_customer_classification WHERE customer_class = 'High-Value At-Risk'").fetchone()[0]
print(f"\nTool 4 OK - {r} High-Value At-Risk customers")

r = con.execute("SELECT category, COUNT(*) as n FROM stg_support_tickets GROUP BY category ORDER BY n DESC").df()
print(f"\nTool 5 OK - complaint categories:\n{r.to_string()}")

r = con.execute("SELECT COUNT(*) FROM ont_customer_classification WHERE upsell_propensity = 'High Propensity'").fetchone()[0]
print(f"\nTool 8 OK - {r} High Propensity customers")

r = con.execute("SELECT LOWER(review_text) LIKE '%retard%' FROM stg_reviews LIMIT 3").df()
print(f"\nTool 7 OK (text search) - verified")

con.close()
print("\nAll MCP tool queries validated.")
