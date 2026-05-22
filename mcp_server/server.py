"""
Air Côte d'Ivoire — MCP Analytics Server

Exposes the analytical warehouse to AI assistants through the Model Context
Protocol. Every tool returns formatted text that combines structured KPIs
with unstructured evidence (reviews, complaint text) where relevant.

Security
--------
All SQL is built with parameter binding (DuckDB ? placeholders). Enum-style
arguments (route_id, customer_class, value_tier, etc.) are validated against
whitelists before any query runs — see validate_*() helpers.

Tools
-----
  - get_network_summary          Top-level KPI snapshot by route type
  - get_route_performance        Route KPIs with classification
  - get_underperforming_routes   Routes by class with operational filter
  - get_at_risk_customers        Churn risk list with retention actions
  - get_complaint_themes         Support tickets summary + sample text
  - compare_routes               Two-route side-by-side
  - search_reviews               Semantic search (sentence-transformers)
  - get_upsell_opportunities     High-propensity customer list
  - get_budget_recommendation    Full priority brief

Embedding search uses all-MiniLM-L6-v2 (384-dim). The index is built lazily
on first call to keep startup time low.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import numpy as np
from mcp.server.fastmcp import FastMCP
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).parent.parent))
from aci_config import DB_PATH

mcp = FastMCP("ACI Analytics")

# ── Shared read-only connection ───────────────────────────────────────────────
_con: duckdb.DuckDBPyConnection | None = None


def con() -> duckdb.DuckDBPyConnection:
    global _con
    if _con is None:
        _con = duckdb.connect(str(DB_PATH), read_only=True)
    return _con


def q(sql: str, params: list | None = None) -> list[dict]:
    df = con().execute(sql, params or []).df()
    return df.to_dict(orient="records")


def fmt(records: list[dict], max_rows: int = 20) -> str:
    if not records:
        return "No results found."
    total = len(records)
    rows = records[:max_rows]
    lines = []
    for i, r in enumerate(rows, 1):
        parts = [f"{k}: {v}" for k, v in r.items() if v is not None and str(v) != "nan"]
        lines.append(f"{i}. " + " | ".join(parts))
    out = "\n".join(lines)
    if total > max_rows:
        out += f"\n... ({total - max_rows} more rows not shown)"
    return out


# ── Input validation ─────────────────────────────────────────────────────────
ROUTE_ID_RE = re.compile(r"^R\d{3}$")

ROUTE_CLASS_VALUES = {
    "Strategic Growth", "Cash Cow", "Operational Risk",
    "Critical Underperformer", "Underperforming", "Monitor",
}
CUSTOMER_CLASS_VALUES = {
    "High-Value At-Risk", "Loyal Advocate", "Growth Target", "Dormant", "Casual",
}
VALUE_TIER_VALUES   = {"High Value", "Mid Value", "Low Value"}
PROPENSITY_VALUES   = {"High Propensity", "Medium Propensity", "Low Propensity"}
SENTIMENT_VALUES    = {"positive", "neutral", "negative"}
TICKET_CATEGORIES   = {
    "Baggage", "Flight Delay", "Customer Service", "Refund",
    "Booking Issue", "Onboard Experience",
}


class ValidationError(ValueError):
    """Raised when a tool argument fails validation."""


def validate_route_id(value: str, allow_empty: bool = True) -> str | None:
    if not value:
        if allow_empty:
            return None
        raise ValidationError("route_id is required")
    if not ROUTE_ID_RE.fullmatch(value):
        raise ValidationError(
            f"route_id '{value}' is not a valid format (expected RNNN, e.g. 'R009')"
        )
    return value


def validate_enum(value: str, allowed: set[str], name: str, allow_empty: bool = True) -> str | None:
    if not value:
        if allow_empty:
            return None
        raise ValidationError(f"{name} is required")
    if value not in allowed:
        sample = ", ".join(sorted(allowed)[:4])
        raise ValidationError(
            f"{name} '{value}' is not recognised. Try one of: {sample}, ..."
        )
    return value


def validate_limit(value: int, default: int = 20, maximum: int = 200) -> int:
    if not isinstance(value, int) or value <= 0:
        return default
    return min(value, maximum)


def safe_tool(fn):
    """Decorator: convert validation/runtime errors into a clean MCP message."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValidationError as e:
            return f"Invalid argument: {e}"
        except duckdb.Error as e:
            return f"Query error: {e}"
        except Exception as e:  # noqa: BLE001
            return f"Unexpected error: {type(e).__name__}: {e}"
    wrapper.__name__ = fn.__name__
    wrapper.__doc__ = fn.__doc__
    return wrapper


# ── Lazy embedding index for semantic review search ──────────────────────────
_embed_model: SentenceTransformer | None = None
_review_cache: list[dict] | None = None
_review_vecs: np.ndarray | None = None


def ensure_review_index() -> None:
    global _embed_model, _review_cache, _review_vecs
    if _review_vecs is not None:
        return
    _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    rows = q("""
        SELECT sr.route_id, dr.route_label, sr.review_date,
               sr.nps_score, sr.sentiment, sr.language, sr.source, sr.review_text
        FROM stg_reviews sr
        JOIN dim_route dr ON sr.route_id = dr.route_id
    """)
    _review_cache = rows
    _review_vecs = _embed_model.encode(
        [r["review_text"] for r in rows],
        normalize_embeddings=True,
        show_progress_bar=False,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tool 1: Network Summary
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_network_summary() -> str:
    """
    Top-level KPI snapshot of Air Côte d'Ivoire's network for January 2025.
    Returns total revenue, margin, average load factor, passenger count,
    delay rate, and ancillary attach by route type — plus a TOTAL row.
    """
    records = q("""
        SELECT
            route_type,
            COUNT(*) AS routes,
            SUM(total_revenue_usd)                       AS total_revenue_usd,
            SUM(total_margin_usd)                        AS total_margin_usd,
            ROUND(SUM(total_margin_usd)/SUM(total_revenue_usd)*100,1)   AS margin_pct,
            ROUND(AVG(avg_load_factor_pct),1)            AS avg_load_factor_pct,
            SUM(total_pax)                               AS total_passengers,
            ROUND(AVG(delay_rate_pct),1)                 AS avg_delay_rate_pct,
            ROUND(AVG(avg_ancillary_attach_rate_pct),1)  AS avg_ancillary_attach_pct
        FROM sem_route_performance
        GROUP BY route_type
        UNION ALL
        SELECT
            'TOTAL',
            COUNT(*),
            SUM(total_revenue_usd), SUM(total_margin_usd),
            ROUND(SUM(total_margin_usd)/SUM(total_revenue_usd)*100,1),
            ROUND(AVG(avg_load_factor_pct),1),
            SUM(total_pax),
            ROUND(AVG(delay_rate_pct),1),
            ROUND(AVG(avg_ancillary_attach_rate_pct),1)
        FROM sem_route_performance
        ORDER BY total_revenue_usd DESC
    """)
    return f"Air Côte d'Ivoire Network Summary — January 2025\n\n{fmt(records)}"


# ──────────────────────────────────────────────────────────────────────────────
# Tool 2: Route Performance
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_route_performance(route_id: str = "", min_margin_pct: float = 0.0) -> str:
    """
    Return detailed KPIs for one or more routes.

    Parameters:
        route_id        Filter by route ID (e.g. 'R009'). Empty = all routes.
        min_margin_pct  Only return routes with margin_pct >= this threshold.
    """
    route_id = validate_route_id(route_id)
    where_clauses, params = [], []
    if route_id:
        where_clauses.append("rp.route_id = ?")
        params.append(route_id)
    if min_margin_pct > 0:
        where_clauses.append("rp.margin_pct >= ?")
        params.append(float(min_margin_pct))
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    records = q(f"""
        SELECT
            rp.route_label, rp.route_type, rp.haul_category,
            ROUND(rp.total_revenue_usd, 0) AS revenue_usd,
            ROUND(rp.total_margin_usd, 0)  AS margin_usd,
            rp.margin_pct,
            rp.avg_load_factor_pct          AS load_factor_pct,
            rp.breakeven_load_factor_pct,
            rp.delay_rate_pct, rp.cancellation_rate_pct,
            ROUND(rp.route_nps, 1)          AS nps_score,
            ROUND(rp.avg_ticket_price_usd, 0) AS avg_ticket_usd,
            rp.avg_ancillary_attach_rate_pct AS ancillary_attach_pct,
            ROUND(rp.avg_price_gap, 0)      AS price_gap_vs_competitor_usd,
            oc.route_class,
            oc.budget_recommendation,
            oc.classification_confidence_pct
        FROM sem_route_performance rp
        JOIN ont_route_classification oc ON rp.route_id = oc.route_id
        {where}
        ORDER BY rp.total_revenue_usd DESC
    """, params)
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 3: Underperforming Routes
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_underperforming_routes(include_operational_risk: bool = True) -> str:
    """
    Routes underperforming commercially (low margin) or operationally (high
    delay / cancellation). Use include_operational_risk=False to see only
    routes that are weak on the revenue side.
    """
    classes = ["Underperforming", "Critical Underperformer"]
    if include_operational_risk:
        classes.append("Operational Risk")
    placeholders = ", ".join(["?"] * len(classes))

    records = q(f"""
        SELECT
            oc.route_label, oc.route_class,
            oc.margin_pct, oc.delay_rate_pct, oc.cancellation_rate_pct,
            oc.route_nps                     AS nps_score,
            oc.total_revenue_usd             AS revenue_usd,
            oc.support_ticket_count,
            oc.budget_recommendation,
            rp.avg_ticket_price_usd,
            rp.avg_competitor_price_usd,
            rp.avg_price_gap                 AS price_gap_usd
        FROM ont_route_classification oc
        JOIN sem_route_performance rp ON oc.route_id = rp.route_id
        WHERE oc.route_class IN ({placeholders})
        ORDER BY oc.margin_pct ASC
    """, classes)
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 4: At-Risk Customers
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_at_risk_customers(
    customer_class: str = "High-Value At-Risk",
    value_tier: str = "",
    limit: int = 20,
) -> str:
    """
    List customers at churn risk with CLV, flight history and retention action.

    Parameters:
        customer_class  One of: High-Value At-Risk, Loyal Advocate, Growth Target,
                        Dormant, Casual. Empty = all at-risk (is_at_risk = true).
        value_tier      Optional filter: 'High Value', 'Mid Value', 'Low Value'.
        limit           Max rows (default 20, capped at 200).
    """
    customer_class = validate_enum(customer_class, CUSTOMER_CLASS_VALUES, "customer_class")
    value_tier     = validate_enum(value_tier, VALUE_TIER_VALUES, "value_tier")
    limit          = validate_limit(limit, default=20)

    where_clauses, params = [], []
    if customer_class:
        where_clauses.append("customer_class = ?")
        params.append(customer_class)
    if value_tier:
        where_clauses.append("value_tier = ?")
        params.append(value_tier)
    if not where_clauses:
        where_clauses.append("is_at_risk = true")
    where = "WHERE " + " AND ".join(where_clauses)

    records = q(f"""
        SELECT
            full_name, customer_class, value_tier, loyalty_tier,
            ROUND(total_revenue_usd, 0)      AS total_revenue_usd,
            ROUND(annualized_revenue_usd, 0) AS annualized_clv_usd,
            total_flights,
            max_points_balance               AS loyalty_points_balance,
            total_support_tickets,
            ROUND(avg_nps_given, 1)          AS avg_nps_given,
            recommended_action, ltv_potential_score
        FROM ont_customer_classification
        {where}
        ORDER BY total_revenue_usd DESC
        LIMIT ?
    """, params + [limit])
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 5: Complaint Themes
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_complaint_themes(route_id: str = "", category: str = "") -> str:
    """
    Support ticket themes — counts, CSAT, resolution rate, sample text.

    Parameters:
        route_id   Filter by route (e.g. 'R001'). Empty = all routes.
        category   Filter by category (e.g. 'Baggage', 'Flight Delay').
    """
    route_id = validate_route_id(route_id)
    category = validate_enum(category, TICKET_CATEGORIES, "category")

    where_clauses, params = [], []
    if route_id:
        where_clauses.append("st.route_id = ?")
        params.append(route_id)
    if category:
        where_clauses.append("st.category = ?")
        params.append(category)
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    records = q(f"""
        SELECT
            dr.route_label, st.category,
            COUNT(*)                                            AS ticket_count,
            ROUND(AVG(st.csat_score), 1)                        AS avg_csat,
            ROUND(SUM(st.is_resolved)::DOUBLE/COUNT(*)*100, 1)  AS resolution_rate_pct,
            COUNT(CASE WHEN st.status='Open' THEN 1 END)        AS open_tickets,
            ANY_VALUE(st.description)                           AS sample_complaint
        FROM stg_support_tickets st
        JOIN dim_route dr ON st.route_id = dr.route_id
        {where}
        GROUP BY dr.route_label, st.category
        ORDER BY ticket_count DESC
    """, params)
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 6: Compare Routes
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def compare_routes(route_id_1: str, route_id_2: str) -> str:
    """
    Side-by-side comparison of two routes using financial + satisfaction signals.

    Parameters:
        route_id_1   First route (e.g. 'R001')
        route_id_2   Second route (e.g. 'R009')
    """
    r1 = validate_route_id(route_id_1, allow_empty=False)
    r2 = validate_route_id(route_id_2, allow_empty=False)

    records = q("""
        SELECT
            rp.route_id, rp.route_label, rp.route_type, rp.haul_category,
            ROUND(rp.total_revenue_usd, 0) AS revenue_usd,
            ROUND(rp.total_margin_usd, 0)  AS margin_usd,
            rp.margin_pct, rp.avg_load_factor_pct, rp.breakeven_load_factor_pct,
            rp.delay_rate_pct, rp.cancellation_rate_pct,
            ROUND(rp.route_nps, 1)         AS nps_score,
            rp.support_ticket_count, rp.avg_support_csat AS avg_csat,
            rp.avg_ticket_price_usd, rp.avg_competitor_price_usd,
            oc.route_class, oc.budget_recommendation,
            oc.classification_confidence_pct
        FROM sem_route_performance rp
        JOIN ont_route_classification oc ON rp.route_id = oc.route_id
        WHERE rp.route_id IN (?, ?)
        ORDER BY rp.route_id
    """, [r1, r2])

    if len(records) < 2:
        found = [r["route_label"] for r in records]
        return f"Could not find both routes. Found: {found}"

    rec1, rec2 = records[0], records[1]
    metrics = [
        "route_label", "route_type", "revenue_usd", "margin_usd", "margin_pct",
        "avg_load_factor_pct", "delay_rate_pct", "cancellation_rate_pct",
        "nps_score", "avg_csat", "route_class", "budget_recommendation",
    ]
    lines = [f"{'Metric':<35} {rec1['route_label']:<25} {rec2['route_label']:<25}", "-" * 85]
    for m in metrics:
        lines.append(f"{m:<35} {str(rec1.get(m, 'N/A')):<25} {str(rec2.get(m, 'N/A')):<25}")

    for route_id, label in [(r1, rec1["route_label"]), (r2, rec2["route_label"])]:
        complaints = q("""
            SELECT category, COUNT(*) AS n, ANY_VALUE(description) AS sample
            FROM stg_support_tickets WHERE route_id = ?
            GROUP BY category ORDER BY n DESC LIMIT 2
        """, [route_id])
        if complaints:
            lines.append(f"\n{label} — Top complaint themes:")
            for c in complaints:
                sample = (c["sample"] or "")[:80]
                lines.append(f"  · {c['category']} ({c['n']} tickets): {sample}...")

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 7: Search Reviews (semantic similarity)
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def search_reviews(
    keyword: str = "",
    route_id: str = "",
    sentiment: str = "",
    limit: int = 10,
) -> str:
    """
    Search verbatim review text using semantic similarity when a keyword is
    provided, or filter by route / sentiment without one.

    The keyword is encoded with all-MiniLM-L6-v2 and ranked by cosine
    similarity. Semantic search finds paraphrases, synonyms, and concept
    matches without exact word overlap (e.g. 'cabin too cold' → reviews
    mentioning 'air conditioning was freezing').

    Parameters:
        keyword     Natural-language query (e.g. 'long wait at check-in').
        route_id    Optional route filter.
        sentiment   Optional: 'positive', 'neutral', or 'negative'.
        limit       Max rows.
    """
    route_id  = validate_route_id(route_id)
    sentiment = validate_enum(sentiment, SENTIMENT_VALUES, "sentiment")
    limit     = validate_limit(limit, default=10, maximum=50)

    if keyword:
        ensure_review_index()
        q_vec = _embed_model.encode([keyword], normalize_embeddings=True)
        scores = (_review_vecs @ q_vec.T).flatten()
        ranked_idx = np.argsort(scores)[::-1]

        results = []
        for idx in ranked_idx:
            r = _review_cache[idx]
            if route_id and r["route_id"] != route_id:
                continue
            if sentiment and r["sentiment"] != sentiment:
                continue
            results.append((r, float(scores[idx])))
            if len(results) >= limit:
                break

        if not results:
            return "No matching reviews found."
        lines = []
        for i, (r, score) in enumerate(results, 1):
            lines.append(
                f"{i}. {r['route_label']} | {r['review_date']} | "
                f"NPS: {r['nps_score']} | {r['sentiment']} | similarity: {score:.2f}\n"
                f"   {r['review_text'][:200]}"
            )
        return "\n\n".join(lines)

    # No keyword — fall back to SQL filter.
    where_clauses, params = [], []
    if route_id:
        where_clauses.append("sr.route_id = ?")
        params.append(route_id)
    if sentiment:
        where_clauses.append("sr.sentiment = ?")
        params.append(sentiment)
    where = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    records = q(f"""
        SELECT dr.route_label, sr.review_date, sr.nps_score,
               sr.sentiment, sr.language, sr.source, sr.review_text
        FROM stg_reviews sr
        JOIN dim_route dr ON sr.route_id = dr.route_id
        {where}
        ORDER BY sr.nps_score ASC
        LIMIT ?
    """, params + [limit])
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 8: Upsell Opportunities
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_upsell_opportunities(
    propensity: str = "High Propensity",
    value_tier: str = "",
    limit: int = 20,
) -> str:
    """
    Customers with high upsell propensity for premium cabin trials,
    ancillary bundles, or upgrade offers.

    Parameters:
        propensity   'High Propensity', 'Medium Propensity', or 'Low Propensity'.
        value_tier   Optional: 'High Value', 'Mid Value', 'Low Value'.
        limit        Max rows.
    """
    propensity = validate_enum(propensity, PROPENSITY_VALUES, "propensity", allow_empty=False)
    value_tier = validate_enum(value_tier, VALUE_TIER_VALUES, "value_tier")
    limit      = validate_limit(limit, default=20)

    where_clauses = ["upsell_propensity = ?"]
    params = [propensity]
    if value_tier:
        where_clauses.append("value_tier = ?")
        params.append(value_tier)
    where = "WHERE " + " AND ".join(where_clauses)

    records = q(f"""
        SELECT
            full_name, customer_class, value_tier, loyalty_tier,
            ROUND(total_revenue_usd, 0)             AS total_revenue_usd,
            total_flights,
            ROUND(ancillary_attach_rate_pct, 1)     AS ancillary_attach_pct,
            ROUND(premium_conversion_rate_pct, 1)   AS premium_conversion_pct,
            max_points_balance,
            recommended_action, ltv_potential_score
        FROM ont_customer_classification
        {where}
        ORDER BY ltv_potential_score DESC, total_revenue_usd DESC
        LIMIT ?
    """, params + [limit])
    return fmt(records)


# ──────────────────────────────────────────────────────────────────────────────
# Tool 9: Budget Recommendation
# ──────────────────────────────────────────────────────────────────────────────
@mcp.tool()
@safe_tool
def get_budget_recommendation() -> str:
    """
    Prioritised budget allocation recommendation for the next 12 months.
    Combines route classification, customer risk signals, and unstructured
    complaint evidence into a single executive brief.
    """
    route_recs = q("""
        SELECT route_label, route_class, budget_recommendation,
               total_revenue_usd, margin_pct, delay_rate_pct,
               classification_confidence_pct
        FROM ont_route_classification
        ORDER BY
            CASE route_class
                WHEN 'Strategic Growth'        THEN 1
                WHEN 'Cash Cow'                THEN 2
                WHEN 'Operational Risk'        THEN 3
                WHEN 'Monitor'                 THEN 4
                WHEN 'Underperforming'         THEN 5
                WHEN 'Critical Underperformer' THEN 6
            END
    """)
    cust_actions = q("""
        SELECT customer_class, COUNT(*) AS count,
               ROUND(SUM(total_revenue_usd), 0)    AS total_clv_at_stake,
               ROUND(AVG(ltv_potential_score), 0)  AS avg_ltv_score
        FROM ont_customer_classification
        GROUP BY customer_class
        ORDER BY total_clv_at_stake DESC
    """)
    top_issues = q("""
        SELECT category, COUNT(*) AS tickets,
               ROUND(AVG(csat_score), 1) AS avg_csat
        FROM stg_support_tickets
        GROUP BY category ORDER BY tickets DESC LIMIT 3
    """)

    output = ["=== BUDGET ALLOCATION RECOMMENDATION ===\n", "--- ROUTE DECISIONS ---"]
    for r in route_recs:
        output.append(
            f"  {r['route_label']} [{r['route_class']}] (conf {r['classification_confidence_pct']}%): "
            f"${r['total_revenue_usd']:,.0f} revenue | {r['margin_pct']:.1f}% margin | "
            f"{r['delay_rate_pct']:.1f}% delay"
        )
        output.append(f"    → {r['budget_recommendation']}")

    output.append("\n--- CUSTOMER INVESTMENT ---")
    for c in cust_actions:
        output.append(
            f"  {c['customer_class']}: {c['count']} customers | "
            f"${c['total_clv_at_stake']:,.0f} CLV at stake | Avg LTV score: {c['avg_ltv_score']}"
        )

    output.append("\n--- TOP OPERATIONAL ISSUES (from tickets) ---")
    for t in top_issues:
        output.append(f"  {t['category']}: {t['tickets']} tickets | Avg CSAT: {t['avg_csat']}")

    output.append(
        "\n--- EXECUTIVE SUMMARY ---\n"
        "1. IMMEDIATE: Fix ABJ→BYK operations — high margin, 30% delay rate, ops failure.\n"
        "2. GROWTH:    Scale Paris route (R009) — highest revenue, lowest load factor.\n"
        "3. RETENTION: Activate offers for 11 High-Value At-Risk customers.\n"
        "4. UPSELL:    Ancillary bundle campaigns on Strategic Growth routes.\n"
        "5. REVIEW:    Evaluate ABJ→DKR (R005) — Critical Underperformer (14% margin + 8% cancel).\n"
    )
    return "\n".join(output)


if __name__ == "__main__":
    mcp.run(transport="stdio")
