"""Smoke test the MCP server's tool functions from inside the container.

Verifies module import, tool invocation, structured + unstructured paths, and
input-validation behaviour. Not part of the public flow — run via:

    docker compose run --rm --entrypoint python mcp scripts/test_mcp_in_container.py
"""
import sys
sys.path.insert(0, "/app/mcp_server")
import server  # noqa: E402


def head(label: str) -> None:
    print(f"\n=== {label} ===")


head("Tools registered")
TOOLS = [
    "get_network_summary", "get_route_performance", "get_underperforming_routes",
    "get_at_risk_customers", "get_complaint_themes", "compare_routes",
    "search_reviews", "get_upsell_opportunities", "get_budget_recommendation",
]
for t in TOOLS:
    fn = getattr(server, t, None)
    print(f"  {'✓' if callable(fn) else '✗'} {t}")

head("get_route_performance('R009')")
print(server.get_route_performance("R009")[:300])

head("SQL injection attempt is rejected")
print(server.get_route_performance("R001' OR '1'='1"))

head("Invalid enum is rejected")
print(server.get_at_risk_customers("XXX"))

head("get_budget_recommendation() (first 6 lines)")
print("\n".join(server.get_budget_recommendation().splitlines()[:6]))

head("search_reviews semantic search")
print(server.search_reviews("morning delays bouake", limit=2)[:500])

print("\nAll MCP smoke checks executed without exception.")
