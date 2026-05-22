# Part 2 — Modeling, Semantic Layer, Ontology

This document maps each Part 2 brief requirement to its concrete artefact in the repo.

---

## Brief: "Build a model that supports the three business themes"

| Business theme | Model that supports it | KPI examples |
|---|---|---|
| Route optimisation & growth | `sem_route_performance` (12 rows) + `ont_route_classification` | margin_pct, avg_load_factor_pct, delay_rate_pct, route_nps, yield_cents_per_pax_km |
| Customer retention | `fact_customer_value` + `sem_customer_segments` + `ont_customer_classification` | annualized_revenue_usd, churn_risk_label, total_flights, customer_class |
| Upsell / cross-sell | `sem_customer_segments.upsell_propensity` + `fact_booking.fare_class` rollups | ancillary_attach_rate_pct, premium_conversion_rate_pct, upsell_propensity |

All three themes are exposed through the dashboard pages 1–3 and the MCP tools.

---

## Brief: "Star schema, Data Vault, or hybrid — justify the choice"

**Choice: Star schema.** Rationale recorded in [`architecture.md`](architecture.md):

- Executive analytics workloads benefit from pre-aggregated dimensional tables, not Data Vault's historisation guarantees.
- Single source system → no need for hub/link/satellite reconciliation.
- Streamlit and MCP both consume pre-aggregated semantic tables — a Data Vault would force them through extra joins.
- Reproducibility and clarity matter more than auditability for a one-shot analytical brief.

Star schema core:

- **Fact tables:** `fact_flight` (480 rows), `fact_booking` (11,475 rows), `fact_customer_value` (300 rows)
- **Dimensions:** `dim_route`, `dim_customer`, `dim_date`

---

## Brief: "Business-friendly semantic layer with KPI definitions, joins, naming conventions"

The `semantic/` folder contains four tables, each with a single canonical KPI definition that downstream consumers must use.

| Semantic table | KPIs | Consumers |
|---|---|---|
| `sem_route_performance` | 25+ commercial / operational / satisfaction / competitive | dashboard pages 1, 4 + MCP tools |
| `sem_customer_segments` | value_tier, upsell_propensity, retention_action | dashboard pages 2, 3 + MCP tools |
| `sem_weekly_kpis` | weekly time series per route | dashboard trend chart |
| `sem_monthly_kpis` | cross-section by route_type × haul_category | executive summaries |

**Naming convention:**

- `*_pct` = percentage (0–100)
- `*_usd` = US dollars
- `*_min` = minutes
- `is_*` / `has_*` = boolean
- Plural noun for counts (`total_flights`, `support_ticket_count`)

Thresholds that drive segments are defined as **dbt variables** in `dbt_project.yml`:

```yaml
vars:
  reference_date: "2025-02-01"
  value_tier_high_threshold: 17000   # p80 of customer revenue distribution
  value_tier_mid_threshold:  13000   # p33 of customer revenue distribution
```

This lets analysts re-tune segment boundaries without touching SQL.

---

## Brief: "Ontology-inspired layer with reasoning rules (e.g. High-Value At-Risk Customer or Strategic but Underperforming Route)"

The `ontology/` folder contains two reasoning tables. Each implements:

1. **Observed properties** as boolean columns (`is_profitable`, `is_at_risk`, `has_scale_potential`, …)
2. **Multi-signal class inference** as a priority-ordered `CASE` expression
3. **Actionable recommendation** parallel to the class
4. **Confidence quantification** as `classification_confidence_pct` (0–100) for `ont_route_classification`, or `ltv_potential_score` (0–100) for `ont_customer_classification`

### Route ontology classes (`ont_route_classification`)

| Class | Inference rule | Budget recommendation |
|---|---|---|
| Strategic Growth | margin ≥50 ∧ delay <10 ∧ cancel <5 | Invest: expand frequency or upsell premium cabin |
| Operational Risk | margin ≥40 ∧ (delay ≥20 ∨ cancel ≥5) | Fix Operations: reliability issues limiting revenue |
| Cash Cow | margin ≥40 ∧ delay <20 | Protect: defend pricing and market share |
| Critical Underperformer | margin <20 ∧ (delay >15 ∨ cancel >5) | Restructure: review viability |
| Underperforming | margin <25 | Improve Revenue Mix: premium + ancillary |
| Monitor | fallback | Watch and measure |

### Customer ontology classes (`ont_customer_classification`)

| Class | Inference rule | Recommended action |
|---|---|---|
| High-Value At-Risk | value=High ∧ total_flights <36 | Priority retention offer: upgrade voucher or bonus miles |
| Loyal Advocate | tier_rank ≥3 ∧ flights ≥39 ∧ Maintain | Reward + cross-sell partner offers |
| Growth Target | value≥Mid ∧ propensity ≥Medium ∧ Maintain | Upsell campaign: premium cabin trial |
| Dormant | total_flights <20 | Re-engagement: targeted reactivation discount |
| Casual | fallback | Nurture: standard loyalty communications |

In a production system, these rules would live in a SHACL schema or be loaded into a reasoning engine (Stardog, Apache Jena). Here they sit in SQL so they can be reasoned about by any tool that speaks SQL, including the MCP server.

---

## Brief: "Show how unstructured data is integrated"

Two unstructured sources, both with two parallel paths into analytics:

### `stg_reviews` — NPS + verbatim text

- **Structured path:** `nps_score → nps_category (Promoter/Passive/Detractor)` rolled up via `fact_flight.nps_score` and `sem_route_performance.route_nps`.
- **Unstructured path:** `review_text` is exposed to the MCP `search_reviews` tool, which builds a sentence-transformer embedding index (`all-MiniLM-L6-v2`) on first call and ranks by cosine similarity. AI assistants can cite verbatim evidence in answers.

### `stg_support_tickets` — Complaint logs

- **Structured path:** `category + csat_score + is_resolved` → `sem_route_performance.support_ticket_count` and `avg_support_csat`.
- **Unstructured path:** `description` is exposed via `get_complaint_themes` (sample text per category) and `compare_routes` (top 2 complaints per route).

**Correlation guarantee.** Ticket route assignment is weighted by route delay + cancellation rate, so R001's 30% delay rate drives the highest "Flight Delay" ticket count, and R005's 8% cancellation rate drives the highest "Refund" ticket count. The `03_validate_data.py` script asserts a Spearman rank correlation ≥ 0.3 between operational stress and ticket volume — currently ~0.83.

---

## Quality Strategy

Two complementary test suites:

1. **dbt column tests** — `models/**/schema.yml` declares 106 `not_null`, `unique`, `accepted_values`, and `relationships` tests using the dbt 1.11 `arguments:` syntax. Run via `cd dbt_project; dbt test --profiles-dir .`.
2. **System-level data quality checks** — `scripts/03_validate_data.py` enforces invariants that don't fit in column tests: revenue conservation across layers, business-rule bounds (margin in ±100%, at least one Strategic Growth route, etc.), ticket/ops correlation, and reference-date freeze.

Both are part of the standard pipeline and must return zero failures before any change is shipped. Both exit non-zero on failure for CI integration.
