# Part 4 — Agentic AI (MCP)

This document maps each Part 4 brief requirement to its concrete artefact and provides a smoke-test guide for evaluators.

---

## Brief: "Expose your modeled data through a small MCP server"

The MCP server lives at [`mcp_server/server.py`](../mcp_server/server.py) and uses FastMCP (the official Anthropic MCP Python SDK).

```
AI Assistant (Claude / Cursor / any MCP client)
    ↓  MCP protocol (stdio transport)
mcp_server/server.py
    ↓  DuckDB read_only connection (shared, lazy)
data/aci.duckdb
    ├── ont_route_classification     ← structured reasoning
    ├── ont_customer_classification  ← structured reasoning
    ├── sem_route_performance        ← canonical KPIs
    ├── sem_customer_segments        ← customer KPIs + segments
    ├── stg_reviews                  ← unstructured text + NPS
    └── stg_support_tickets          ← unstructured complaint text
```

**Wiring it up.** Add to your MCP client config (Claude Desktop example):

```json
{
  "mcpServers": {
    "aci-analytics": {
      "command": "python",
      "args": ["c:/Analytic Engineer/air-cote-divoire/mcp_server/server.py"]
    }
  }
}
```

A repo-local config is provided at [`mcp_server/mcp_config.json`](../mcp_server/mcp_config.json).

---

## Brief: "AI interface must use both structured data and at least one unstructured source"

| Tool | Structured | Unstructured |
|---|---|---|
| `get_network_summary` | KPIs by route_type | — |
| `get_route_performance` | 12+ KPIs + class + recommendation | — |
| `get_underperforming_routes` | margin, delay, cancel | — |
| `get_at_risk_customers` | CLV, flights, points, score | — |
| `get_complaint_themes` | counts, CSAT, resolution rate | **Representative ticket description text** |
| `compare_routes` | side-by-side metrics | **Top 2 complaint samples per route** |
| `search_reviews` | NPS filter, sentiment filter | **Semantic similarity ranking over review_text** |
| `get_upsell_opportunities` | propensity, premium conv, LTV score | — |
| `get_budget_recommendation` | full ontology brief | **Top 3 complaint categories cited** |

The structured ↔ unstructured pairing is the senior differentiator: every recommendation surfaced by the AI can be backed by both a number and a verbatim quote.

---

## Brief: "Demonstrate grounded questions"

Smoke-test prompts that should each route to the right tool:

| Prompt | Expected tool | Expected evidence |
|---|---|---|
| "Which routes deserve more budget next quarter?" | `get_budget_recommendation` | Strategic Growth + Cash Cow routes prioritised, Critical Underperformer flagged |
| "Which high-value customers are at risk?" | `get_at_risk_customers` | List of 11 named customers, each with CLV + retention action |
| "What complaints are driving low satisfaction on R001?" | `get_complaint_themes(route_id='R001')` | Flight Delay tops the list, sample tickets cite morning delays |
| "Compare R001 and R009 on financials and satisfaction" | `compare_routes('R001', 'R009')` | Side-by-side + 2 complaint themes per route |
| "Find reviews mentioning long check-in waits" | `search_reviews('long check-in waits')` | Semantically ranked reviews even without exact word overlap |
| "Which customers should we upsell to Business?" | `get_upsell_opportunities` | Ranked by LTV score, filtered by propensity |
| "Show me underperforming routes that aren't just ops issues" | `get_underperforming_routes(include_operational_risk=False)` | Only Critical Underperformer + Underperforming |

---

## Security Model

Every tool argument is validated against a whitelist or regex before any SQL runs:

- `route_id` must match `^R\d{3}$`
- `customer_class`, `value_tier`, `propensity`, `sentiment`, `category` are whitelisted enums
- `limit` is clamped to 1–200
- All SQL is parameter-bound (DuckDB `?` placeholders); no f-string interpolation of user input
- Errors are caught and returned as clean MCP messages (`@safe_tool` decorator)

An adversarial input like `route_id="R001' OR '1'='1"` is rejected at the validation stage before reaching the database — see `validate_route_id()` in `server.py`.

---

## Semantic Search Implementation

`search_reviews` is the only tool that uses ML beyond rule-based logic.

- Model: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, ~80MB, CPU-friendly)
- Index: built lazily on first call from `stg_reviews.review_text` (~1,700 vectors)
- Ranking: cosine similarity between query embedding and review embeddings
- Filters: `route_id` and `sentiment` apply post-ranking

The lazy index means startup time stays under 2 seconds; the model + index loads on the first semantic-search invocation only.

---

## Demo Recording (To Capture)

The brief requires a short video showing the AI interaction. See [`capture_guide.md`](capture_guide.md) for the recording script.

Recommended demo flow (~3 minutes):

1. Ask: *"What does the airline's network look like?"* → `get_network_summary`
2. Ask: *"Which routes are underperforming?"* → `get_underperforming_routes`
3. Drill into R001: *"Compare R001 to a healthy route like R009"* → `compare_routes`
4. Find evidence: *"Show me negative reviews about morning delays"* → `search_reviews` (semantic)
5. Customer action: *"Who are the at-risk high-value customers I should retain?"* → `get_at_risk_customers`
6. Synthesis: *"Give me the budget recommendation"* → `get_budget_recommendation`

Each turn should show the AI calling the right tool, the tool returning structured + unstructured evidence, and the AI synthesising a grounded answer.
