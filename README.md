# Air Côte d'Ivoire — Analytics Engineer Challenge

**Decision question:** Where should Air Côte d'Ivoire invest first to maximise profitable growth — route expansion, customer retention, or upsell / cross-sell?

> Senior submission. Canonical dbt pipeline. Two-tier test suite (`dbt test` + system invariants). Hardened MCP server with semantic review search. Data-driven decision layer in the dashboard.

---

## Architecture

```
air-cote-divoire/
├── aci_config.py            ← Reads dbt_project.yml vars; constants used by Python scripts
├── requirements.txt         ← Pinned Python deps (host venv + Docker)
├── Dockerfile               ← python:3.12-slim + deps + pre-cached embedding model
├── docker-compose.yml       ← services: pipeline / dashboard / mcp / dbt-docs
├── Makefile                 ← shortcuts: make build / pipeline / dashboard / mcp / docs
├── data/
│   ├── source/              ← Starter Excel (ships with the repo)
│   ├── aci.duckdb           ← Single-file analytical warehouse (generated)
│   ├── raw/                 ← CSVs exported from the Excel
│   └── synthetic/           ← Generated enrichment datasets
├── scripts/
│   ├── 01_load_raw.py            ← Excel → DuckDB raw tables
│   ├── 02_generate_synthetic.py  ← 6 enrichment datasets (route-correlated)
│   └── 03_validate_data.py       ← 12 system-level invariants (post-dbt)
├── dbt_project/             ← Canonical model definitions (.sql + schema.yml)
│   ├── dbt_project.yml      ← Single source of truth: vars + materialisation
│   ├── profiles.yml         ← DuckDB profile
│   └── models/
│       ├── staging/         ← Clean, typed source views
│       ├── marts/           ← Star schema facts + dimensions (tables)
│       ├── semantic/        ← Business KPI tables
│       └── ontology/        ← Classification + inference rules
├── dashboard/
│   └── app.py               ← Streamlit 4-page executive dashboard
├── mcp_server/
│   └── server.py            ← MCP analytics server (9 tools, hardened)
└── docs/
    ├── executive_recommendations.md  ← 1-page exec brief
    ├── architecture.md
    ├── data_dictionary.md
    ├── modeling_diagram.md
    ├── part1_business_understanding.md
    ├── part2_modeling.md
    ├── part4_agentic_ai.md
    └── capture_guide.md             ← How to record screenshots + video
```

---

## Setup & Run

You can run the project **with Docker (recommended for reviewers)** or **with a local Python 3.12 venv**.

---

### Option A — Docker (recommended)

Single image, three services (pipeline / dashboard / MCP), one `make` per workflow.

**Prerequisites:** Docker Desktop or Docker Engine 20.10+ with Compose v2. That's it — no Python install needed on the host.

```powershell
# Build once (~5 min, pre-caches the sentence-transformers model)
make build                  # or: docker compose build

# Run the full pipeline (load → generate → dbt build → validate)
make pipeline               # or: docker compose run --rm pipeline

# Start the dashboard at http://localhost:8501
make dashboard              # or: docker compose up dashboard

# Run the MCP server interactively (stdio)
make mcp                    # or: docker compose run --rm -i mcp

# Browse auto-generated dbt docs at http://localhost:8080
make docs                   # or: docker compose --profile docs up dbt-docs
```

`make help` lists every shortcut. See [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml), [.dockerignore](.dockerignore) for the implementation.

The container persists the warehouse and dbt artefacts back to the host (`./data/aci.duckdb`, `./dbt_project/target/`) via bind mounts, so you can inspect them from your IDE while containers run.

---

### Option B — Local Python venv

**Prerequisites:** Python 3.12 (or any 3.9–3.12). `dbt-duckdb` is not yet compatible with 3.13/3.14.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
# 1. Load + enrich
python scripts/01_load_raw.py
python scripts/02_generate_synthetic.py

# 2. Transform + test (dbt-native)
cd dbt_project
dbt build --profiles-dir .              # run + test + snapshot in one command
dbt docs generate --profiles-dir .       # optional: auto-generated documentation
cd ..

# 3. System-level invariants
python scripts/03_validate_data.py

# 4. Dashboard
streamlit run dashboard/app.py

# 5. MCP
python mcp_server/server.py
```

---

## Data

### Starter (from Excel)

| Table | Rows | Notes |
|-------|------|-------|
| `raw_airports` | 10 | IATA, coordinates, timezone |
| `raw_routes` | 12 | Domestic, regional, international |
| `raw_customers` | 300 | Demographics, loyalty tier, segment |
| `raw_flights` | 480 | January 2025 |
| `raw_bookings` | 11,475 | Fare class, revenue, ancillary |

### Synthetic enrichment

| Table | Rows | Why it matters |
|-------|------|----------------|
| `synth_aircraft_fleet` | 12 | Fuel burn, capacity — enables cost modeling |
| `synth_fare_details` | 12 | Per-route operating cost, breakeven LF |
| `synth_loyalty_activity` | ~2,100 | Point earn/redeem — loyalty engagement signal |
| `synth_customer_reviews` | ~1,700 | NPS + verbatim text (bilingual fr/en) — unstructured |
| `synth_support_tickets` | 1,500 | **Route-correlated:** delay/cancel rates weight ticket volume per route. Spearman ≈ 0.83 |
| `synth_competitor_context` | 264 | Monthly competitor price benchmarks |

---

## Modeling Design

### Star schema (`marts/`)

- **`fact_flight`** — one row per flight, joins bookings + reviews + route economics
- **`fact_booking`** — one row per booking
- **`fact_customer_value`** — one row per customer, CLV + RFM
- **`dim_route`** — route + operating economics + competitor benchmark
- **`dim_customer`** — customer + loyalty + ticket summary
- **`dim_date`** — standard date dimension

### Semantic (`semantic/`)

- **`sem_route_performance`** — 25+ KPIs per route, canonical for dashboard + MCP
- **`sem_customer_segments`** — value_tier, upsell_propensity, retention_action
- **`sem_weekly_kpis`** — weekly time series
- **`sem_monthly_kpis`** — cross-section by route_type × haul_category

### Ontology (`ontology/`)

- **`ont_route_classification`** — `Strategic Growth` / `Cash Cow` / `Operational Risk` / `Critical Underperformer` / `Underperforming` / `Monitor`, plus `budget_recommendation` and `classification_confidence_pct`
- **`ont_customer_classification`** — `High-Value At-Risk` / `Loyal Advocate` / `Growth Target` / `Dormant` / `Casual`, plus `recommended_action` and `ltv_potential_score`

Full mapping in [docs/part2_modeling.md](docs/part2_modeling.md).

---

## Key Findings

| Route | Class | Revenue | Margin | Issue |
|-------|-------|---------|--------|-------|
| R009 ABJ→CDG | Cash Cow | $1.6M | 46% | 10% load factor — biggest scale headroom |
| R001 ABJ→BYK | Operational Risk | $122K | 63.5% | **30% delay rate** destroying NPS |
| R005 ABJ→DKR | Critical Underperformer | $419K | **14%** | 8% cancellation + thin margin |
| R002, R003 | Strategic Growth | $240K | 53% | Reliable ops, grow frequency |

**Budget priorities** (full brief in [docs/executive_recommendations.md](docs/executive_recommendations.md)):

1. Fix R001 operations → protect 63.5% margin
2. Scale R009 (Paris) → biggest revenue upside (10% load factor today)
3. Retain 11 High-Value At-Risk customers ($204K CLV at stake)
4. Restructure R005 reserve
5. Ancillary upsell on Growth Targets + Loyal Advocates (136 high-propensity customers)

---

## MCP Tools

| Tool | Description |
|------|-------------|
| `get_network_summary` | Top-level KPI snapshot by route type |
| `get_route_performance(route_id, min_margin_pct)` | Route KPIs with classification |
| `get_underperforming_routes(include_operational_risk)` | Problem routes |
| `get_at_risk_customers(class, value_tier, limit)` | Churn risk list |
| `get_complaint_themes(route_id, category)` | Support ticket themes + sample text |
| `compare_routes(route_id_1, route_id_2)` | Side-by-side + top complaint themes |
| `search_reviews(keyword, route_id, sentiment)` | **Semantic similarity** (sentence-transformers) |
| `get_upsell_opportunities(propensity, value_tier)` | Upsell target list |
| `get_budget_recommendation()` | Full prioritised brief with evidence |

All tools use parameterised SQL + whitelist validation. SQL injection is rejected at the validation stage. See [docs/part4_agentic_ai.md](docs/part4_agentic_ai.md).

---

## Quality Gates

| Suite | What it checks | Run |
|---|---|---|
| dbt column tests (106) | `not_null`, `unique`, `accepted_values`, `relationships` declared in `models/**/schema.yml` | `cd dbt_project; dbt test --profiles-dir .` |
| System-level invariants (12) | Revenue conservation, business-rule bounds, ticket/ops correlation, reference-date freeze | `python scripts/03_validate_data.py` |

Both must return zero failures before any change ships. Both exit non-zero so they can wire into CI directly.

---

## Visual Deliverables

Capture instructions (screenshots + video walkthrough) live in [docs/capture_guide.md](docs/capture_guide.md). Place outputs in `docs/screenshots/` and `docs/videos/`.

---

## Assumptions & Limitations

- **Operating costs** synthetic but calibrated to real airline benchmarks (fuel $0.85/kg, crew $350/h block, $400 + $0.04/km airport fees).
- **REFERENCE_DATE = 2025-02-01** — frozen analytical anchor. See [docs/architecture.md](docs/architecture.md).
- **Single-month snapshot** — monthly trend analysis requires more periods. The pipeline accepts new data drops without code changes.
- **Sentiment analysis** is keyword/label based; the embedding pipeline (`search_reviews`) is already in place to swap in LLM-based clustering when desired.
- **Competitor pricing** is synthetic; production would integrate Amadeus / Skyscanner.
- **MCP server runs over stdio** — production deployment would use SSE on a cloud host.

---

## Help / Contact

For any reviewer running into setup issues, the validation script reports the most common failures and explains them. If something silently misbehaves, check [docs/architecture.md](docs/architecture.md) → "Single Source of Truth" — the dbt files are canonical, all other artefacts derive from them.
