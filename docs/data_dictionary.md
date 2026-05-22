# Data Dictionary — Air Côte d'Ivoire Analytics

Reference date: **2025-02-01** (frozen — see [architecture.md](architecture.md)).

---

## Staging Layer (`stg_*` views)

### `stg_airports`

| Column | Type | Description |
|--------|------|-------------|
| airport_code | VARCHAR | IATA code (PK) — e.g. ABJ, CDG |
| airport_name | VARCHAR | Full name |
| city / country | VARCHAR | Location |
| timezone | VARCHAR | IANA timezone |
| latitude / longitude | DOUBLE | Coordinates |
| airport_role | VARCHAR | `Hub` (ABJ) / `Domestic` (other CIV) / `International` |

### `stg_routes`

| Column | Type | Description |
|--------|------|-------------|
| route_id | VARCHAR | PK — R001…R012 |
| route_label | VARCHAR | Human-readable label (`R009: ABJ → CDG`) |
| route_type | VARCHAR | `Domestic` / `Regional` / `International` |
| haul_category | VARCHAR | `Domestic` / `Regional` / `Medium-Haul` / `Long-Haul` |
| distance_km | INTEGER | Great-circle distance |
| block_time_min / block_time_h | INT/DBL | Flight duration |
| origin/destination_airport_code | VARCHAR | IATA |

### `stg_customers`

| Column | Type | Description |
|--------|------|-------------|
| customer_id | VARCHAR | PK |
| full_name | VARCHAR | First + last |
| gender / birth_date | | Demographics |
| age_years | INTEGER | Computed against `REFERENCE_DATE` |
| country / city | VARCHAR | Location |
| customer_segment | VARCHAR | `Standard` / `Business` / `Budget` / `Premium` |
| loyalty_tier | VARCHAR | `None` / `Explorer` / `Silver` / `Gold` / `Platinum` |
| loyalty_tier_rank | INTEGER | 0 (None) … 4 (Platinum) |
| signup_date | DATE | |
| tenure_months | INTEGER | Months between signup and `REFERENCE_DATE` |
| preferred_channel | VARCHAR | Web / Mobile App / Agent |

> ~40% of customers have `loyalty_tier = 'None'` (no tier yet). They surface explicitly as `None` rather than being silently bucketed as the lowest tier.

### `stg_flights`

| Column | Type | Description |
|--------|------|-------------|
| flight_id | VARCHAR | PK |
| flight_number | VARCHAR | HF-series code |
| route_id | VARCHAR | FK → stg_routes |
| flight_date | DATE | Operational date |
| flight_year/month/quarter | INTEGER | Date parts |
| scheduled/actual departure/arrival | TIMESTAMP | |
| aircraft_type | VARCHAR | A319, A320, A330-900neo, ATR72 |
| seat_capacity | INTEGER | |
| flight_status | VARCHAR | `On Time` / `Delayed` / `Cancelled` |
| delay_min | INTEGER | Minutes delayed (0 = on time) |
| delay_category | VARCHAR | `On-Time` / `Minor Delay` (≤15m) / `Moderate Delay` (≤60m) / `Major Delay` / `Cancelled` |

### `stg_bookings`

Cancelled bookings are filtered out at this layer.

| Column | Type | Description |
|--------|------|-------------|
| booking_id | VARCHAR | PK |
| booking_date | DATE | |
| customer_id / flight_id | VARCHAR | FKs |
| booking_channel | VARCHAR | Web / Mobile App / Agent / Airport |
| fare_class | VARCHAR | `Economy` / `Premium Economy` / `Business` / `First` |
| fare_family | VARCHAR | Flex / Standard / Light |
| ticket_price_usd | DOUBLE | |
| ancillary_revenue_usd | DOUBLE | Bags, seat, meals |
| total_revenue_usd | DOUBLE | ticket + ancillary |
| bags_count | INTEGER | |
| seat_selection_flag | INTEGER | 0/1 |
| revenue_category | VARCHAR | `Premium` / `Flexible Economy` / `Standard Economy` |
| has_ancillary / has_seat_selection | INTEGER | 0/1 |

### `stg_reviews` (unstructured)

| Column | Type | Description |
|--------|------|-------------|
| review_id | VARCHAR | PK |
| flight_id / route_id | VARCHAR | FKs |
| review_date | DATE | |
| nps_score | INTEGER | 0–10 |
| nps_category | VARCHAR | `Promoter` (9–10) / `Passive` (7–8) / `Detractor` (0–6) |
| sentiment | VARCHAR | `positive` / `neutral` / `negative` |
| review_text | VARCHAR | Verbatim |
| language | VARCHAR | `fr` / `en` |
| source | VARCHAR | App / Email Survey / Web / TripAdvisor |

### `stg_support_tickets` (unstructured)

| Column | Type | Description |
|--------|------|-------------|
| ticket_id | VARCHAR | PK |
| customer_id / route_id | VARCHAR | FKs |
| open_date | DATE | |
| category | VARCHAR | `Baggage` / `Flight Delay` / `Customer Service` / `Refund` / `Booking Issue` / `Onboard Experience` |
| description | VARCHAR | Free-text complaint |
| sentiment | VARCHAR | `negative` / `neutral` |
| status | VARCHAR | `Open` / `Resolved` |
| resolution_days | INTEGER | Days to resolve (null if Open) |
| csat_score | INTEGER | 1–5 (null if Open) |
| ticket_domain | VARCHAR | `Operational` (Baggage/Flight Delay) / `Commercial` (CS/Refund) / `Product` (Booking/Onboard) |
| is_resolved | INTEGER | 0/1 |

> Route assignment is weighted by route delay + cancellation rate. Spearman rank correlation between operational stress and ticket count is ≈ 0.83 — see `scripts/03_validate_data.py`.

### `stg_loyalty`

| Column | Type | Description |
|--------|------|-------------|
| activity_id | VARCHAR | PK |
| customer_id | VARCHAR | FK |
| activity_date | DATE | |
| activity_type | VARCHAR | earn_flight / earn_bonus / redeem_upgrade / redeem_voucher / tier_upgrade |
| points_change | INTEGER | Signed (negative for redemptions) |
| running_balance | INTEGER | Post-event balance |
| tier_after | VARCHAR | Tier after the event |
| channel | VARCHAR | App / Web / Agent / Kiosk |
| is_earn / is_redeem | INTEGER | 0/1 |

---

## Marts Layer (`fact_*`, `dim_*` tables)

### `fact_flight`

One row per flight — central operational fact joining bookings, reviews, route economics.

| Column | Description |
|--------|-------------|
| booked_seats | Confirmed bookings count |
| load_factor_pct | booked_seats / seat_capacity × 100 |
| ticket_revenue_usd | Sum of ticket prices |
| ancillary_revenue_usd | Sum of ancillary revenue |
| total_revenue_usd | ticket + ancillary |
| estimated_margin_usd | total_revenue − route operating cost |
| ancillary_attach_rate_pct | % of passengers with ancillary purchase |
| review_count / promoter_count / detractor_count | Per-flight review aggregates |
| nps_score | Per-flight NPS = (promoters − detractors) / total × 100 |

### `fact_booking`

One row per booking. Grain: one passenger on one flight.

### `fact_customer_value`

One row per customer. Aggregated CLV + RFM signals.

| Column | Description |
|--------|-------------|
| annualized_revenue_usd | total_revenue × 12 / tenure_months |
| booking_frequency_per_month | total_bookings / tenure_months |
| ancillary_attach_rate_pct | bookings_with_ancillary / total_bookings × 100 |
| premium_conversion_rate_pct | premium_bookings / total_bookings × 100 |
| days_since_last_booking | Days from last booking to `REFERENCE_DATE` (frozen) |
| churn_risk_label | `High Risk` (>180d + ≥3 flights) / `Medium Risk` (>90d) / `Low Risk` |

---

## Semantic Layer (`sem_*` tables)

### `sem_route_performance` — 25+ KPIs per route

| KPI | Formula |
|-----|---------|
| margin_pct | total_margin_usd / total_revenue_usd × 100 |
| avg_load_factor_pct | mean of per-flight load_factor_pct |
| delay_rate_pct | flights with >15 min delay / total × 100 |
| cancellation_rate_pct | cancelled / total × 100 |
| route_nps | (promoters − detractors) / total_reviews × 100 |
| yield_cents_per_pax_km | total_revenue / (total_pax × distance_km) × 100 |
| avg_price_gap | ACI avg price − competitor avg price |
| support_ticket_count | tickets per route |
| avg_support_csat | mean CSAT (resolved tickets only) |

### `sem_customer_segments` — Customer-level KPIs + derived segments

| Attribute | Values | Logic |
|-----------|--------|-------|
| value_tier | `High Value` / `Mid Value` / `Low Value` | Revenue ≥ `var('value_tier_high_threshold')` ($17K, p80) / ≥ `var('value_tier_mid_threshold')` ($13K, p33) / below |
| upsell_propensity | `High` / `Medium` / `Low Propensity` | Premium conv >15% OR tier rank ≥3 / 35+ flights AND >50% attach / fallback |
| retention_action | `Priority Retain` / `Retain` / `Maintain` | flights <30 / <37 / ≥37 |
| churn_risk_label | inherited from `fact_customer_value` |

### `sem_weekly_kpis` and `sem_monthly_kpis`

- `sem_weekly_kpis`: weekly time series per route (60 rows for 4 weeks × 12 routes + a couple of partial weeks).
- `sem_monthly_kpis`: cross-section by `route_type × haul_category` for executive comparisons.

---

## Ontology Layer (`ont_*` tables)

### `ont_route_classification`

Multi-signal route inference.

| Class | Criteria | Budget recommendation |
|-------|----------|-----------------------|
| Strategic Growth | margin ≥50 ∧ delay <10 ∧ cancel <5 | Invest: expand frequency or upsell premium cabin |
| Operational Risk | margin ≥40 ∧ (delay ≥20 ∨ cancel ≥5) | Fix Operations |
| Cash Cow | margin ≥40 ∧ delay <20 | Protect: defend pricing |
| Critical Underperformer | margin <20 ∧ (delay >15 ∨ cancel >5) | Restructure |
| Underperforming | margin <25 | Improve Revenue Mix |
| Monitor | fallback | Watch and measure |

Plus boolean attributes: `is_profitable`, `is_operationally_stressed`, `is_high_satisfaction`, `has_scale_potential`, `is_demand_strong_ops_weak`.

`classification_confidence_pct` (0–100) quantifies how much evidence (flight count, review count, ticket count) supports the class.

### `ont_customer_classification`

Multi-signal customer inference.

| Class | Criteria | Action |
|-------|----------|--------|
| High-Value At-Risk | value=High ∧ flights <36 | Priority retention offer: upgrade voucher or bonus miles |
| Loyal Advocate | tier_rank ≥3 ∧ flights ≥39 ∧ Maintain | Reward + cross-sell partners |
| Growth Target | value ≥Mid ∧ propensity ≥Medium ∧ Maintain | Upsell campaign: premium cabin trial |
| Dormant | flights <20 | Re-engagement: targeted reactivation discount |
| Casual | fallback | Nurture: standard loyalty comms |

Plus boolean attributes: `is_high_value`, `is_at_risk`, `is_loyalty_advocate`, `is_upsell_target`, `is_dormant`, `is_high_complaint_rate`.

`ltv_potential_score` (0-100) composite:

- value_tier (40 pts)
- loyalty_tier_rank (20 pts)
- upsell_propensity (20 pts)
- churn_risk = Low (20 pts)
