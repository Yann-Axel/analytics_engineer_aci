# Part 1 — Business Understanding & Data Generation

## Decision Question

> **Where should Air Côte d'Ivoire invest first to maximize profitable growth: route expansion and optimization, customer retention, or upsell / cross-sell?**

---

## 1. Airline Business Domains

### 1.1 Network Domain
The network domain covers the routes, airports, and capacity decisions that define where ACI can fly and how efficiently it uses its fleet.

**Key concepts:**
- **Route portfolio** — 12 routes from Abidjan (ABJ): 3 domestic, 6 regional (West Africa), 3 international (Paris CDG, Lagos LOS, Accra ACC)
- **Fleet assignment** — matching aircraft type to route economics (ATR72 for short domestic; A330-900neo for Paris)
- **Load factor** — the percentage of available seats filled; drives revenue and determines whether a route covers its operating costs
- **Breakeven load factor** — the minimum occupancy needed to cover fuel, crew, and airport fees per flight

**Why it matters for the decision:** A route can generate high revenue but still destroy value if its breakeven is 30% and it only fills 16% of seats. Conversely, a route that seems unprofitable may be suffering from an operational failure (delays, cancellations) rather than weak demand — these require different budget interventions.

---

### 1.2 Operations Domain
Operations covers the reliability and efficiency of flight execution: on-time performance, aircraft utilization, and disruption management.

**Key concepts:**
- **Delay rate** — share of flights with significant delays (>60 min); directly drives customer dissatisfaction and NPS
- **Cancellation rate** — cancelled flights destroy revenue and erode trust
- **Aircraft utilization** — average flying hours per day; underutilized aircraft means wasted fixed cost
- **Block time** — scheduled flight duration; used to compute fuel burn and crew cost

**Why it matters for the decision:** Route R001 (Abidjan–Bouaké) has the highest margin in the network (63.5%) but a 30% delay rate — customer reviews explicitly cite "retard systématique". Without fixing operations, investing in capacity growth on that route would amplify dissatisfaction, not revenue.

---

### 1.3 Commercial Domain
The commercial domain covers pricing, fare structures, competitive positioning, and channel management.

**Key concepts:**
- **Fare class / fare family** — Economy vs. Business vs. First; Flex vs. Standard vs. Light fares carry different margins
- **Yield** (revenue per passenger per kilometre) — the airline industry's primary revenue efficiency metric; comparable across routes of different distances
- **Pricing position vs. competitors** — ACI charges a premium (+$12/ticket avg) vs. regional competitors; important for demand elasticity
- **Booking channel** — Web, Mobile App, Agent, Airport; each has different cost-to-serve and ancillary conversion

**Why it matters for the decision:** The Paris route (R009) generates the highest absolute revenue ($1.6M) but has a 10% load factor — it's underselling. The gap between current and potential revenue at 70% load factor is ~$9.6M. Commercial investment (diaspora marketing, GDS distribution, corporate contracts) is the lever.

---

### 1.4 Customer Domain
The customer domain covers who flies with ACI, how loyal they are, and where churn risk concentrates.

**Key concepts:**
- **Customer segment** — Standard, Frequent, Corporate; drives willingness-to-pay and service expectations
- **Loyalty tier** — Bronze / Silver / Gold / Platinum; measures depth of relationship and influences repeat purchase
- **Customer Lifetime Value (CLV)** — annualized revenue per customer based on booking frequency and spend
- **Churn risk** — the likelihood a high-value customer stops flying ACI; measured here by below-median flight frequency relative to peers
- **Satisfaction (NPS)** — Net Promoter Score from post-flight reviews; links operations to commercial outcomes

**Key finding:** 300 customers generated $4.4M in January 2025 alone — average $14,700/customer. Eleven customers (top 4% by revenue, $18,500 avg) are classified High-Value At-Risk. Retaining each is worth more than acquiring three new standard customers.

---

### 1.5 Ancillary Revenue Domain
Ancillary revenue covers all revenue beyond the base ticket: baggage fees, seat selection, meals, upgrades, and loyalty redemptions.

**Key concepts:**
- **Ancillary attach rate** — percentage of passengers purchasing at least one ancillary product; ~50% in this dataset
- **Revenue per passenger** — total passenger yield including ancillary; more actionable than ticket price alone
- **Upsell propensity** — likelihood a customer will accept a premium offer (upgrade, seat, bundle) based on past behaviour and loyalty tier
- **Ancillary mix** — bags vs. seat selection vs. meals; understanding the mix helps tailor offer bundles

**Why it matters for the decision:** Ancillary already represents a significant share of total revenue. With 107 customers identified as High Propensity for upsell, a targeted offer campaign (premium cabin trial, ancillary bundle) could materially increase revenue per booking without adding a single new seat.

---

## 2. KPI Framework

### Network KPIs
| KPI | Formula | Decision use |
|-----|---------|--------------|
| Route Revenue | SUM(ticket_price + ancillary) per route | Identifies revenue drivers |
| Route Margin % | (Revenue – Operating Cost) / Revenue | Profitability health check |
| Load Factor % | Booked seats / Available seats | Capacity efficiency |
| Breakeven Load Factor | Operating Cost / (Seats × Avg Fare) | Profitability threshold |
| Yield (¢/pax·km) | Revenue / (Passengers × Distance) | Cross-route revenue efficiency |
| Avg Delay (min) | Mean delay_min per flight | Operational reliability |
| Delay Rate % | Delayed flights / Total flights | Reliability benchmark |
| Cancellation Rate % | Cancelled / Total flights | Extreme reliability failure |

### Customer KPIs
| KPI | Formula | Decision use |
|-----|---------|--------------|
| Repeat Booking Rate | % customers with ≥2 flights | Loyalty signal |
| Booking Frequency | Bookings / Tenure months | Engagement depth |
| Annualized CLV | Annual revenue per customer | Retention priority |
| Churn Risk Score | Flight count relative to peer median | At-risk identification |
| NPS Score | (Promoters – Detractors) / Total × 100 | Satisfaction benchmark |
| Loyalty Points Balance | Current miles/points balance | Loyalty program health |
| Avg CSAT | Mean CSAT from resolved tickets | Service quality |

### Upsell / Ancillary KPIs
| KPI | Formula | Decision use |
|-----|---------|--------------|
| Ancillary Attach Rate | Bookings with ancillary / Total | Offer penetration |
| Ancillary Revenue % | Ancillary / Total Revenue | Mix health |
| Premium Conversion Rate | Business/First bookings / Total | Upgrade yield |
| Revenue per Passenger | Total revenue / PAX | Offer effectiveness |
| Upsell Propensity | Rule-based score (tier + behaviour) | Campaign targeting |
| LTV Potential Score | Composite (value + loyalty + propensity) | Prioritisation score |

---

## 3. Synthetic Data Created

### Why enrich beyond the starter data?

The starter dataset provides the **what** (flights, bookings, customers) but not the **why** — operating costs, customer satisfaction, competitive context, and loyalty engagement are invisible without enrichment. The six synthetic datasets below make the difference between a dashboard that shows revenue and a decision tool that explains *where to invest next*.

### 3.1 `aircraft_fleet` — 12 rows
**What:** Tail numbers, aircraft type specs (fuel burn kg/h, seat capacity, max range, ownership).
**Why:** Enables per-flight fuel cost calculation. Without fuel burn data, operating cost is zero and margin is meaningless. A330-900neo burns 5,800 kg/h vs. 1,100 kg/h for ATR72 — this difference explains why domestic routes can be profitable at low fares while long-haul requires higher prices.
**Impact on recommendations:** Makes the Paris route's breakeven load factor calculable (17.9%) vs. domestic (26-30%).

### 3.2 `fare_details` — 12 rows
**What:** Per-route fuel cost, crew cost, airport fees, total operating cost, breakeven load factor, synthetic competitor price.
**Why:** The core margin calculation requires knowing cost per flight. Without it, a "high revenue" route and a "high margin" route are indistinguishable.
**Impact on recommendations:** Reveals that R001 (ABJ-BYK, 63.5% margin) is far more profitable than R005 (ABJ-DKR, 14.3% margin) despite similar passenger volumes — leading to different investment recommendations.

### 3.3 `loyalty_activity` — 1,994 rows
**What:** Point earn/redeem events per customer (earn_flight, redeem_upgrade, tier_upgrade, etc.).
**Why:** Loyalty engagement is a leading indicator of customer retention. A Platinum customer who hasn't earned points recently is more likely to churn than their tier suggests.
**Impact on recommendations:** Enriches `dim_customer` with `max_points_balance` and `loyalty_event_count`, which feed into the customer ontology classification.

### 3.4 `customer_reviews` — 1,220 rows *(unstructured)*
**What:** Post-flight NPS scores (0–10) + verbatim review text in French and English, with sentiment labels (positive / neutral / negative) and source (App, Email, TripAdvisor).
**Why:** Structured operational data (delay_min) explains *what happened*. Reviews explain *how customers felt* and *why they will or won't come back*. The MCP tool `search_reviews` lets the AI assistant surface verbatim evidence for any recommendation.
**Impact on recommendations:** Reviews on R001 consistently mention "retard systématique le matin" — the text evidence directly supports the "Fix Operations" recommendation. Reviews on R002/R003 are more positive, supporting "Strategic Growth" classification.

### 3.5 `support_tickets` — 1,500 rows *(unstructured)*
**What:** Customer complaint logs with category (Baggage, Flight Delay, Refund, Booking Issue, etc.), description text, resolution status, and CSAT score.
**Why:** Tickets quantify the operational failure surface. A route with high delay rate AND high ticket volume on "Flight Delay" category is operationally stressed from two independent signals — stronger evidence than either alone.
**Impact on recommendations:** R005 (ABJ-DKR) has both 8% cancellation rate AND the highest delay ticket count — reinforcing the "Critical Underperformer / Restructure" recommendation.

### 3.6 `competitor_context` — 264 rows
**What:** Monthly average ticket prices from named competitors per route (Starbow, Air France, Ethiopian, ASKY, etc.) for 12 months.
**Why:** Margin analysis without competitive context is incomplete. ACI could have a 40% margin but be leaving money on the table if competitors charge 30% more; or it could be at risk of losing volume if competitors undercut.
**Impact on recommendations:** On R009 (Paris), ACI's pricing is broadly in line with Air France — the load factor gap is therefore a distribution/marketing problem, not a pricing problem.

---

## 4. Assumptions

| Assumption | Value | Rationale |
|------------|-------|-----------|
| Jet fuel price | $0.85/kg | IATA 2025 West Africa benchmark |
| Crew cost | $350/block hour | Industry average for narrow/wide-body |
| Airport fees | $400 fixed + $0.04/km | Abidjan landing fee proxy |
| Churn risk proxy | Flight count vs. peer median | All bookings are Jan 2025; days-since-last-booking would make everyone look "at risk" in 2026 |
| NPS text generation | Route-specific issue templates | Based on stated operational issues (e.g. R001 delay, R005 cancellations) |
| Competitor prices | Base fare × random multiplier ± 25% | Directionally correct for West Africa competitive context |
| Value tier thresholds | Percentile-based (p33=$13K, p80=$17K) | Calibrated to actual revenue distribution in the dataset |
