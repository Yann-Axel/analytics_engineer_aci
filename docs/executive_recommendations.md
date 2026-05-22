# Executive Recommendations — Air Côte d'Ivoire Growth Allocation

**Period analysed:** January 2025 • 12 routes • 300 customers • 11,475 bookings
**Decision question:** Where should ACI invest first to maximise profitable growth?

---

## Headline Answer

**Three concurrent levers, in this priority:**

1. **Fix R001 (ABJ → BYK)** — protect a 63.5% margin route bleeding NPS through delays.
2. **Scale R009 (ABJ → CDG, Paris)** — biggest revenue and biggest capacity headroom.
3. **Retain 11 High-Value At-Risk customers** — fastest CLV protection, lowest spend.

Routes 4–12 are managed through the existing playbook (Cash Cow defence, ancillary upsell). One route (R005, ABJ → DKR) is the only candidate for restructuring.

---

## 1. Network — Where Money Is Made and Lost

| Class | Routes | Revenue | Action |
|---|---|---|---|
| Strategic Growth | R002, R003 | $240K | Invest in frequency + premium cabin |
| Cash Cow | R004, R007, R009, R010, R012 | $2.76M | Defend pricing, protect margins |
| Operational Risk | **R001** | $122K | **Fix ops — 30% delay rate destroying NPS (-11)** |
| Critical Underperformer | **R005** | $419K | **Restructure — 14% margin + 8% cancellation** |
| Underperforming | R011 | $228K | Improve revenue mix (premium + ancillary) |
| Monitor | R006, R008 | $645K | Watch quarterly |

**Two structural observations:**

- **R009 (Paris) is 36% of total network revenue with a 10% load factor.** The A330-900neo runs at 29 of 290 seats. The economic upside from doubling load factor is materially larger than any other lever on the table.
- **R001 has the highest margin in the network (63.5%) but the worst operational reliability** (30% of flights with significant delays). Verbatim reviews repeatedly cite *"retard systématique"*. The intervention is operational (ground crew, scheduling), not commercial.

---

## 2. Customers — Who To Keep, Who To Grow

| Class | Customers | Annual CLV | Priority |
|---|---|---|---|
| **High-Value At-Risk** | **11** | **$204K** | Immediate retention offer |
| Loyal Advocate | 15 | $270K | Reward + cross-sell partners |
| Growth Target | 121 | $2.05M | Upsell campaign — premium trial |
| Casual | 153 | $1.89M | Nurture, standard comms |

**The 11 High-Value At-Risk customers represent the highest leverage retention spend:** average $14.9K annualised CLV each, below-median flight frequency relative to peers, no operational signal explaining their drop. Re-engagement cost (upgrade vouchers, bonus miles) is tiny relative to the CLV protected.

---

## 3. Ancillary & Upsell — A Tail That Pays For Itself

- Ancillary attach rate averages ~50% across the network.
- 136 customers carry "High" or "Medium" upsell propensity (premium conversion > 15% or Gold/Platinum tier).
- The lowest-cost initiative on the priority matrix: ancillary bundle campaigns, 1-3 month time to value, no operational dependency.

---

## Recommended 12-Month Budget Allocation

| Bucket | Share | Rationale |
|---|---|---|
| Growth Route Investment | ~45% | Scale R009 (Paris) + defend Cash Cow routes (R004, R007, R009, R010, R012). Distribution, corporate contracts, capacity. |
| Retention Program | 20% | Personalised offers for 11 High-Value At-Risk + targeted reactivation of 121 Growth Targets. |
| Route Restructuring Reserve | ~12% | Restructure R005 (Dakar). Hold for R011 if 90-day improvement plan fails. |
| Ancillary Upsell | 10% | Bundle campaigns + premium cabin trials. |
| Network Operations Fix | ~8% | R001 reliability spend (ground crew, scheduling, communications). |

> Network bucket sizes are proportional to revenue at stake within each strategy. See dashboard Page 4 for the live computation.

---

## Why This Is Defensible

- Every route classification carries a `classification_confidence_pct` (0–100) derived from data volume (flights, reviews, tickets). The Strategic Growth and Cash Cow recommendations sit at 100% confidence; Underperforming sits at ~95%. Only an Emerging-volume route would warrant pause-and-watch.
- Every recommendation links to **both** structured KPIs (margin, delay rate, NPS) **and** unstructured evidence (verbatim reviews, complaint themes). The MCP server `compare_routes()` and `get_complaint_themes()` tools surface the evidence trail on demand.
- The 11 High-Value At-Risk customers are individually identifiable — no segment-level abstraction. Marketing can act on the named list within 24 hours.

---

## Risks and What Would Change This Brief

| Risk | Trigger to revisit |
|---|---|
| R005 restructure premature if Q2 cancellation rate halves | Re-run pipeline with Feb–Apr 2025 data |
| Paris load factor gap explained by aircraft mismatch, not demand | Compare 290-seat A330 vs 165-seat A320neo seat economics |
| Some High-Value At-Risk customers are seasonal, not churning | Add Q2 booking signal once available |
| Sentiment-driven recommendations may over-weight a few extreme reviewers | Rotate to LLM-embedding clustering (already prototyped in `search_reviews`) |
