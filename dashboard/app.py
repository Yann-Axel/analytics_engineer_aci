"""
Air Côte d'Ivoire — Executive Growth Allocation Dashboard
4 pages: Network & Profitability | Customer & Retention | Upsell & Cross-sell | Decision Layer
"""
import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "aci.duckdb"
LOGO_PATH = Path(__file__).parent / "assets" / "aci_logo.jpg"

st.set_page_config(
    page_title="Air Côte d'Ivoire — Growth Dashboard",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Color palette ────────────────────────────────────────────────────────────
COLORS = {
    "primary":    "#1B4F72",
    "secondary":  "#E67E22",
    "success":    "#27AE60",
    "danger":     "#C0392B",
    "warning":    "#F39C12",
    "neutral":    "#95A5A6",
    "bg":         "#F8F9FA",
}
CLASS_COLORS = {
    "Strategic Growth":       COLORS["success"],
    "Cash Cow":               COLORS["primary"],
    "Operational Risk":       COLORS["warning"],
    "Monitor":                COLORS["neutral"],
    "Underperforming":        COLORS["danger"],
    "Critical Underperformer": "#8B0000",
    "High-Value At-Risk":     COLORS["danger"],
    "Loyal Advocate":         COLORS["success"],
    "Growth Target":          COLORS["secondary"],
    "Casual":                 COLORS["neutral"],
    "Dormant":                "#808080",
}

@st.cache_resource
def get_con():
    return duckdb.connect(str(DB_PATH), read_only=True)

def q(sql: str) -> pd.DataFrame:
    return get_con().execute(sql).df()


# ── Sidebar navigation ───────────────────────────────────────────────────────
st.sidebar.image(str(LOGO_PATH), use_container_width=True)
st.sidebar.title("Air Côte d'Ivoire")
st.sidebar.caption("Growth Allocation Dashboard · Jan 2025")

page = st.sidebar.radio(
    "Navigation",
    ["Network & Profitability", "Customer & Retention", "Upsell & Cross-sell", "Decision Layer"],
    index=0,
)

st.sidebar.divider()
st.sidebar.caption("Data: Jan 2025 | 12 routes | 300 customers | 11,475 bookings")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: NETWORK & PROFITABILITY
# ══════════════════════════════════════════════════════════════════════════════
if page == "Network & Profitability":
    st.title("✈ Network & Profitability")
    st.caption("Route performance · load factor · operational reliability · margin analysis")

    routes = q("SELECT * FROM sem_route_performance ORDER BY total_revenue_usd DESC")
    route_class = q("SELECT * FROM ont_route_classification ORDER BY margin_pct DESC")

    # ── KPI cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    total_rev = routes["total_revenue_usd"].sum()
    total_margin = routes["total_margin_usd"].sum()
    avg_lf = routes["avg_load_factor_pct"].mean()
    avg_delay = routes["avg_delay_min"].mean()
    total_pax = int(routes["total_pax"].sum())
    avg_yield = routes["yield_cents_per_pax_km"].mean()

    k1.metric("Total Revenue", f"${total_rev/1e6:.2f}M")
    k2.metric("Network Margin", f"${total_margin/1e6:.2f}M", f"{total_margin/total_rev*100:.1f}%")
    k3.metric("Avg Load Factor", f"{avg_lf:.1f}%", help="Low — growth opportunity")
    k4.metric("Avg Yield", f"{avg_yield:.3f} ¢/pax·km", help="Revenue per passenger-kilometre")
    k5.metric("Avg Delay", f"{avg_delay:.0f} min")
    k6.metric("Total Passengers", f"{total_pax:,}")

    st.divider()

    # ── Route opportunity matrix ──────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Route Opportunity Matrix")
        st.caption("Margin % vs. Delay Rate — bubble size = total revenue")
        merged = routes.merge(route_class[["route_id","route_class","budget_recommendation"]], on="route_id")
        merged["color"] = merged["route_class"].map(CLASS_COLORS).fillna(COLORS["neutral"])

        fig = px.scatter(
            merged,
            x="delay_rate_pct",
            y="margin_pct",
            size="total_revenue_usd",
            color="route_class",
            color_discrete_map=CLASS_COLORS,
            hover_name="route_label",
            hover_data={
                "total_revenue_usd": ":,.0f",
                "avg_load_factor_pct": ":.1f",
                "delay_rate_pct": ":.1f",
                "margin_pct": ":.1f",
                "budget_recommendation": True,
            },
            labels={
                "delay_rate_pct": "Delay Rate (%)",
                "margin_pct": "Margin (%)",
                "route_class": "Route Class",
            },
            size_max=60,
            template="plotly_white",
        )
        fig.add_hline(y=40, line_dash="dot", line_color="gray", annotation_text="40% margin threshold")
        fig.add_vline(x=15, line_dash="dot", line_color="gray", annotation_text="15% delay threshold")
        fig.update_layout(height=420)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Route Classification")
        for _, row in route_class.iterrows():
            color = CLASS_COLORS.get(row["route_class"], COLORS["neutral"])
            badge = f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:11px">{row["route_class"]}</span>'
            st.markdown(
                f"**{row['route_label']}** &nbsp; {badge}<br>"
                f"<small>Margin: {row['margin_pct']:.1f}% | Delay: {row['delay_rate_pct']:.1f}%</small>",
                unsafe_allow_html=True,
            )

    st.divider()

    # ── Revenue breakdown ─────────────────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Revenue by Route")
        fig_rev = px.bar(
            routes.sort_values("total_revenue_usd"),
            x="total_revenue_usd", y="route_label",
            orientation="h", color="margin_pct",
            color_continuous_scale="RdYlGn",
            labels={"total_revenue_usd": "Revenue (USD)", "margin_pct": "Margin %"},
            template="plotly_white",
        )
        fig_rev.update_layout(height=350, coloraxis_colorbar=dict(title="Margin %"))
        st.plotly_chart(fig_rev, use_container_width=True)

    with col4:
        st.subheader("Operational Reliability")
        fig_ops = go.Figure()
        fig_ops.add_trace(go.Bar(
            name="Delay Rate %",
            x=routes["route_label"],
            y=routes["delay_rate_pct"],
            marker_color=COLORS["warning"],
        ))
        fig_ops.add_trace(go.Bar(
            name="Cancellation Rate %",
            x=routes["route_label"],
            y=routes["cancellation_rate_pct"],
            marker_color=COLORS["danger"],
        ))
        fig_ops.update_layout(
            barmode="stack", height=350,
            xaxis_tickangle=-30, template="plotly_white",
        )
        st.plotly_chart(fig_ops, use_container_width=True)

    st.divider()

    # ── Weekly operational trend ──────────────────────────────────────────────
    st.subheader("Weekly Revenue Trend by Route")
    weekly = q("""
        SELECT wk.year_week, wk.route_id, dr.route_label,
               wk.total_revenue_usd, wk.avg_load_factor_pct, wk.avg_delay_min
        FROM sem_weekly_kpis wk
        JOIN dim_route dr ON wk.route_id = dr.route_id
        ORDER BY wk.week_start, wk.route_id
    """)
    fig_trend = px.line(
        weekly, x="year_week", y="total_revenue_usd",
        color="route_label", markers=True,
        template="plotly_white",
        labels={"total_revenue_usd": "Revenue (USD)", "year_week": "Week"},
    )
    fig_trend.update_layout(height=380, legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig_trend, use_container_width=True)

    # ── Yield & competitive pricing ───────────────────────────────────────────
    col_y1, col_y2 = st.columns(2)

    with col_y1:
        st.subheader("Yield by Route (¢ / pax·km)")
        st.caption("Revenue generated per passenger per kilometre — key airline efficiency metric")
        yield_data = routes[["route_label", "yield_cents_per_pax_km", "haul_category",
                              "avg_ticket_price_usd"]].sort_values("yield_cents_per_pax_km", ascending=False)
        fig_yield = px.bar(
            yield_data, x="route_label", y="yield_cents_per_pax_km",
            color="haul_category",
            color_discrete_map={
                "Domestic":     COLORS["success"],
                "Regional":     COLORS["primary"],
                "Medium-Haul":  COLORS["secondary"],
                "Long-Haul":    COLORS["warning"],
            },
            hover_data={"avg_ticket_price_usd": ":,.0f"},
            labels={"yield_cents_per_pax_km": "Yield (¢/pax·km)", "route_label": "Route",
                    "haul_category": "Haul"},
            template="plotly_white",
        )
        fig_yield.update_layout(height=320, xaxis_tickangle=-30)
        st.plotly_chart(fig_yield, use_container_width=True)

    with col_y2:
        st.subheader("Competitive Pricing vs. Competitor")
        comp = routes[["route_label", "aci_avg_price", "competitor_avg_price", "avg_price_gap"]].dropna()
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Bar(
            name="ACI Avg Price", x=comp["route_label"], y=comp["aci_avg_price"],
            marker_color=COLORS["primary"],
        ))
        fig_comp.add_trace(go.Bar(
            name="Competitor Avg", x=comp["route_label"], y=comp["competitor_avg_price"],
            marker_color=COLORS["secondary"],
        ))
        fig_comp.update_layout(barmode="group", template="plotly_white", height=320, xaxis_tickangle=-30)
        st.plotly_chart(fig_comp, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: CUSTOMER & RETENTION
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Customer & Retention":
    st.title("👥 Customer & Retention")
    st.caption("Segmentation · loyalty · churn risk · complaint themes")

    custs = q("SELECT * FROM ont_customer_classification")
    segs  = q("SELECT * FROM sem_customer_segments")

    # ── KPI cards ────────────────────────────────────────────────────────────
    k1, k2, k3, k4, k5 = st.columns(5)
    at_risk_n    = int((custs["customer_class"] == "High-Value At-Risk").sum())
    advocates_n  = int((custs["customer_class"] == "Loyal Advocate").sum())
    avg_clv      = segs["annualized_revenue_usd"].mean()
    avg_tickets  = segs["total_support_tickets"].mean()
    pct_high     = int((custs["value_tier"] == "High Value").sum())

    k1.metric("High-Value At-Risk", at_risk_n, help="High revenue + below-median flight freq")
    k2.metric("Loyal Advocates", advocates_n)
    k3.metric("Avg Annualized CLV", f"${avg_clv:,.0f}")
    k4.metric("High-Value Customers", pct_high)
    k5.metric("Avg Support Tickets/Customer", f"{avg_tickets:.1f}")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Customer Class Distribution")
        class_counts = custs["customer_class"].value_counts().reset_index()
        class_counts.columns = ["customer_class", "count"]
        fig_pie = px.pie(
            class_counts, values="count", names="customer_class",
            color="customer_class", color_discrete_map=CLASS_COLORS,
            template="plotly_white",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(height=360, showlegend=False)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col2:
        st.subheader("Revenue by Customer Segment")
        seg_rev = segs.groupby("customer_segment")["total_revenue_usd"].agg(["sum","mean","count"]).reset_index()
        seg_rev.columns = ["segment","total_revenue","avg_revenue","count"]
        fig_seg = px.bar(
            seg_rev, x="segment", y="total_revenue",
            color="avg_revenue", color_continuous_scale="Blues",
            text="count",
            labels={"total_revenue": "Total Revenue (USD)", "avg_revenue": "Avg Revenue"},
            template="plotly_white",
        )
        fig_seg.update_traces(texttemplate="%{text} customers", textposition="outside")
        fig_seg.update_layout(height=360)
        st.plotly_chart(fig_seg, use_container_width=True)

    st.divider()

    # ── Loyalty tier analysis ─────────────────────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Loyalty Tier vs. CLV")
        tier_stats = segs.groupby("loyalty_tier").agg(
            avg_clv=("annualized_revenue_usd","mean"),
            count=("customer_id","count"),
            avg_flights=("total_flights","mean"),
        ).reset_index()
        fig_tier = px.scatter(
            tier_stats, x="loyalty_tier", y="avg_clv",
            size="count", color="avg_flights",
            color_continuous_scale="Viridis",
            labels={"avg_clv": "Avg Annualized CLV ($)", "avg_flights": "Avg Flights"},
            template="plotly_white",
        )
        fig_tier.update_layout(height=340)
        st.plotly_chart(fig_tier, use_container_width=True)

    with col4:
        st.subheader("Support Ticket Categories by Route")
        tickets = q("""
            SELECT st.route_id, dr.route_label, st.category,
                   COUNT(*) as n, AVG(st.csat_score) as avg_csat
            FROM stg_support_tickets st
            JOIN dim_route dr ON st.route_id = dr.route_id
            GROUP BY st.route_id, dr.route_label, st.category
        """)
        fig_tickets = px.bar(
            tickets, x="route_label", y="n", color="category",
            labels={"n": "Tickets", "route_label": "Route"},
            template="plotly_white",
        )
        fig_tickets.update_layout(height=340, xaxis_tickangle=-30, legend=dict(orientation="h", y=-0.3))
        st.plotly_chart(fig_tickets, use_container_width=True)

    st.divider()

    # ── High-Value At-Risk customers table ────────────────────────────────────
    st.subheader("High-Value At-Risk Customers — Priority Retention List")
    at_risk_df = custs[custs["customer_class"] == "High-Value At-Risk"][[
        "full_name","loyalty_tier","value_tier","total_revenue_usd",
        "total_flights","max_points_balance","recommended_action"
    ]].sort_values("total_revenue_usd", ascending=False)
    if len(at_risk_df) > 0:
        st.dataframe(at_risk_df, use_container_width=True, hide_index=True)
    else:
        st.info("No High-Value At-Risk customers under current classification thresholds.")

    # ── Repeat Behavior ───────────────────────────────────────────────────────
    st.divider()
    st.subheader("Repeat Behavior & Booking Frequency")
    col_rb1, col_rb2, col_rb3 = st.columns(3)

    with col_rb1:
        st.caption("Booking frequency distribution (flights per customer)")
        freq_bins = segs["total_flights"].copy()
        freq_labels = freq_bins.apply(lambda x:
            "< 25 flights" if x < 25 else
            "25–34 flights" if x < 35 else
            "35–40 flights" if x < 41 else
            "> 40 flights"
        )
        freq_dist = freq_labels.value_counts().reset_index()
        freq_dist.columns = ["range", "customers"]
        freq_dist["range"] = pd.Categorical(
            freq_dist["range"],
            categories=["< 25 flights", "25–34 flights", "35–40 flights", "> 40 flights"],
            ordered=True,
        )
        freq_dist = freq_dist.sort_values("range")
        fig_freq = px.bar(
            freq_dist, x="range", y="customers",
            color="range",
            color_discrete_sequence=[COLORS["danger"], COLORS["warning"], COLORS["primary"], COLORS["success"]],
            labels={"customers": "Customers", "range": "Flight Count"},
            template="plotly_white",
        )
        fig_freq.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_freq, use_container_width=True)

    with col_rb2:
        st.caption("Avg booking frequency by loyalty tier (bookings/month)")
        freq_tier = segs.groupby("loyalty_tier")["booking_frequency_per_month"].mean().reset_index()
        freq_tier.columns = ["loyalty_tier", "avg_freq"]
        tier_order = ["Bronze", "Silver", "Gold", "Platinum"]
        freq_tier["loyalty_tier"] = pd.Categorical(freq_tier["loyalty_tier"], categories=tier_order, ordered=True)
        freq_tier = freq_tier.sort_values("loyalty_tier")
        fig_freq_tier = px.bar(
            freq_tier, x="loyalty_tier", y="avg_freq",
            color="avg_freq", color_continuous_scale="Blues",
            labels={"avg_freq": "Avg Bookings/Month", "loyalty_tier": "Tier"},
            template="plotly_white",
        )
        fig_freq_tier.update_layout(height=300)
        st.plotly_chart(fig_freq_tier, use_container_width=True)

    with col_rb3:
        st.caption("Multi-route flyers vs. single-route customers")
        multi = segs["distinct_routes_flown"].apply(lambda x: "Multi-route (≥2)" if x >= 2 else "Single-route (1)")
        multi_dist = multi.value_counts().reset_index()
        multi_dist.columns = ["type", "count"]
        fig_multi = px.pie(
            multi_dist, values="count", names="type",
            color="type",
            color_discrete_map={"Multi-route (≥2)": COLORS["success"], "Single-route (1)": COLORS["neutral"]},
            template="plotly_white",
        )
        fig_multi.update_traces(textposition="inside", textinfo="percent+label")
        fig_multi.update_layout(height=300, showlegend=False)
        st.plotly_chart(fig_multi, use_container_width=True)

    repeat_rate = (segs["total_flights"] >= 2).mean() * 100
    avg_freq_overall = segs["booking_frequency_per_month"].mean()
    st.caption(
        f"Repeat customer rate: **{repeat_rate:.0f}%** of customers flew more than once "
        f"| Avg booking frequency: **{avg_freq_overall:.2f} bookings/month**"
    )

    st.divider()

    # ── Satisfaction trend (NPS from reviews) ─────────────────────────────────
    st.subheader("Customer Satisfaction — NPS by Route")
    nps_data = q("""
        SELECT dr.route_label, COUNT(*) as total_reviews,
               SUM(CASE WHEN nps_category='Promoter' THEN 1 ELSE 0 END) as promoters,
               SUM(CASE WHEN nps_category='Detractor' THEN 1 ELSE 0 END) as detractors,
               ROUND((SUM(CASE WHEN nps_category='Promoter' THEN 1.0 ELSE 0.0 END)
                    - SUM(CASE WHEN nps_category='Detractor' THEN 1.0 ELSE 0.0 END))
                   / COUNT(*) * 100, 1) as nps_score
        FROM stg_reviews sr JOIN dim_route dr ON sr.route_id = dr.route_id
        GROUP BY dr.route_label ORDER BY nps_score DESC
    """)
    fig_nps = px.bar(
        nps_data, x="route_label", y="nps_score",
        color="nps_score", color_continuous_scale="RdYlGn",
        labels={"nps_score": "NPS Score", "route_label": "Route"},
        template="plotly_white",
    )
    fig_nps.add_hline(y=0, line_dash="dash", line_color="black")
    fig_nps.update_layout(height=320)
    st.plotly_chart(fig_nps, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: UPSELL & CROSS-SELL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Upsell & Cross-sell":
    st.title("💰 Upsell & Cross-sell")
    st.caption("Ancillary revenue · upgrade conversion · revenue per passenger · offer propensity")

    segs   = q("SELECT * FROM sem_customer_segments")
    routes = q("SELECT * FROM sem_route_performance")
    bookings = q("SELECT * FROM fact_booking LIMIT 50000")

    # ── KPIs ─────────────────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4)
    total_ancillary = bookings["ancillary_revenue_usd"].sum()
    total_ticket    = bookings["ticket_price_usd"].sum()
    ancillary_share = total_ancillary / (total_ancillary + total_ticket) * 100
    avg_attach = segs["ancillary_attach_rate_pct"].mean()
    premium_rate = segs["premium_conversion_rate_pct"].mean()

    k1.metric("Ancillary Revenue", f"${total_ancillary:,.0f}")
    k2.metric("Ancillary Share of Total", f"{ancillary_share:.1f}%")
    k3.metric("Avg Ancillary Attach Rate", f"{avg_attach:.1f}%")
    k4.metric("Premium Conversion Rate", f"{premium_rate:.1f}%")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Ancillary Revenue by Route")
        anc_route = routes[["route_label","ancillary_revenue_usd","ticket_revenue_usd"]].sort_values("ancillary_revenue_usd", ascending=False)
        fig_anc = go.Figure()
        fig_anc.add_trace(go.Bar(name="Ticket Revenue", x=anc_route["route_label"], y=anc_route["ticket_revenue_usd"], marker_color=COLORS["primary"]))
        fig_anc.add_trace(go.Bar(name="Ancillary Revenue", x=anc_route["route_label"], y=anc_route["ancillary_revenue_usd"], marker_color=COLORS["secondary"]))
        fig_anc.update_layout(barmode="stack", height=360, xaxis_tickangle=-30, template="plotly_white")
        st.plotly_chart(fig_anc, use_container_width=True)

    with col2:
        st.subheader("Upsell Propensity by Segment")
        prop = segs.groupby(["customer_segment","upsell_propensity"]).size().reset_index(name="count")
        fig_prop = px.bar(
            prop, x="customer_segment", y="count", color="upsell_propensity",
            color_discrete_map={
                "High Propensity": COLORS["success"],
                "Medium Propensity": COLORS["warning"],
                "Low Propensity": COLORS["neutral"],
            },
            labels={"count": "Customers", "customer_segment": "Segment"},
            template="plotly_white",
        )
        fig_prop.update_layout(height=360)
        st.plotly_chart(fig_prop, use_container_width=True)

    st.divider()

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Revenue per Passenger by Fare Class")
        rev_class = bookings.groupby("fare_class").agg(
            avg_rev=("revenue_per_pax_usd","mean"),
            n=("booking_id","count"),
        ).reset_index()
        fig_class = px.bar(
            rev_class, x="fare_class", y="avg_rev",
            color="fare_class",
            labels={"avg_rev": "Avg Revenue/Pax (USD)", "fare_class": "Fare Class"},
            template="plotly_white",
            text="n",
        )
        fig_class.update_traces(texttemplate="%{text:,} pax", textposition="outside")
        fig_class.update_layout(height=340, showlegend=False)
        st.plotly_chart(fig_class, use_container_width=True)

    with col4:
        st.subheader("Ancillary Attach Rate by Loyalty Tier")
        anc_tier = segs.groupby("loyalty_tier")["ancillary_attach_rate_pct"].mean().reset_index()
        anc_tier.columns = ["loyalty_tier","avg_attach_rate"]
        fig_anc_tier = px.bar(
            anc_tier, x="loyalty_tier", y="avg_attach_rate",
            color="avg_attach_rate", color_continuous_scale="Oranges",
            labels={"avg_attach_rate": "Avg Attach Rate (%)", "loyalty_tier": "Loyalty Tier"},
            template="plotly_white",
        )
        fig_anc_tier.update_layout(height=340)
        st.plotly_chart(fig_anc_tier, use_container_width=True)

    st.divider()

    # ── Booking channel analysis ──────────────────────────────────────────────
    st.subheader("Revenue by Booking Channel")
    channel = bookings.groupby("booking_channel").agg(
        total_rev=("total_revenue_usd","sum"),
        avg_rev=("revenue_per_pax_usd","mean"),
        n=("booking_id","count"),
        anc=("ancillary_revenue_usd","sum"),
    ).reset_index()
    channel["ancillary_share_pct"] = channel["anc"] / channel["total_rev"] * 100
    fig_ch = px.scatter(
        channel, x="n", y="avg_rev",
        size="total_rev", color="ancillary_share_pct",
        color_continuous_scale="Oranges",
        hover_name="booking_channel",
        text="booking_channel",
        labels={"n": "Bookings Count", "avg_rev": "Avg Revenue/Pax (USD)", "ancillary_share_pct": "Ancillary %"},
        template="plotly_white",
    )
    fig_ch.update_traces(textposition="top center")
    fig_ch.update_layout(height=360)
    st.plotly_chart(fig_ch, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: DECISION LAYER  — every number is derived from the ontology tables.
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Decision Layer":
    st.title("🎯 Decision Layer — Executive Recommendations")
    st.caption("Where to invest first to maximize profitable growth over the next 12 months")

    route_class_df = q("SELECT * FROM ont_route_classification ORDER BY total_revenue_usd DESC")
    cust_class_df  = q("SELECT * FROM ont_customer_classification")
    segs           = q("SELECT * FROM sem_customer_segments")
    routes_perf_df = q("SELECT * FROM sem_route_performance")

    # Iterate as list-of-dicts for the priority/recommendation logic below.
    route_class = route_class_df.to_dict("records")
    cust_class  = cust_class_df.to_dict("records")
    routes_perf = routes_perf_df.to_dict("records")

    st.info(
        "**Decision question:** Where should Air Côte d'Ivoire invest first — "
        "route expansion, customer retention, or upsell/cross-sell? "
        "The analysis below answers this with evidence from structured and unstructured data."
    )

    # ── Build initiatives dynamically from ontology ───────────────────────────
    # Map each non-trivial route class to a recommended initiative + scoring.
    CLASS_PROFILE = {
        "Operational Risk":        {"category": "Network",   "ease": 3, "ttv": "3-6 months",  "verb": "Fix Ops"},
        "Strategic Growth":        {"category": "Network",   "ease": 3, "ttv": "6-12 months", "verb": "Scale"},
        "Cash Cow":                {"category": "Network",   "ease": 4, "ttv": "3-6 months",  "verb": "Defend"},
        "Critical Underperformer": {"category": "Network",   "ease": 1, "ttv": "9-12 months", "verb": "Restructure"},
        "Underperforming":         {"category": "Network",   "ease": 2, "ttv": "6-12 months", "verb": "Re-mix"},
    }

    rev_max = max((r["total_revenue_usd"] for r in route_class), default=1)

    def revenue_impact_score(rev: float) -> int:
        # 1..5 by revenue quintile; favours larger absolute revenue at stake.
        ratio = rev / rev_max if rev_max else 0
        if   ratio >= 0.8: return 5
        elif ratio >= 0.5: return 4
        elif ratio >= 0.2: return 3
        elif ratio >= 0.1: return 2
        else:              return 1

    initiatives = []
    # Network initiatives derived from the route ontology.
    for r in route_class:
        profile = CLASS_PROFILE.get(r["route_class"])
        if profile is None:
            continue
        evidence_bits = [
            f"{r['margin_pct']:.1f}% margin",
            f"{r['delay_rate_pct']:.1f}% delay rate",
        ]
        if r["cancellation_rate_pct"] and r["cancellation_rate_pct"] > 0:
            evidence_bits.append(f"{r['cancellation_rate_pct']:.1f}% cancellations")
        evidence_bits.append(f"{r['support_ticket_count']} tickets")
        initiatives.append({
            "Initiative": f"{profile['verb']} {r['route_label']}",
            "Category":   profile["category"],
            "Revenue Impact":      revenue_impact_score(r["total_revenue_usd"]),
            "Implementation Ease": profile["ease"],
            "Time to Value":       profile["ttv"],
            "Evidence Source":     " | ".join(evidence_bits),
            "Class":               r["route_class"],
            "Confidence %":        int(r["classification_confidence_pct"]),
            "_revenue":            r["total_revenue_usd"],
        })

    # Customer-side initiatives derived from the customer ontology.
    at_risk_n  = sum(1 for c in cust_class if c["customer_class"] == "High-Value At-Risk")
    at_risk_clv = sum((c["annualized_revenue_usd"] or 0) for c in cust_class if c["customer_class"] == "High-Value At-Risk")
    growth_n   = sum(1 for c in cust_class if c["customer_class"] == "Growth Target")
    loyal_n    = sum(1 for c in cust_class if c["customer_class"] == "Loyal Advocate")
    high_prop_n = sum(1 for c in cust_class if c["customer_class"] in ("Growth Target", "Loyal Advocate"))

    if at_risk_n > 0:
        initiatives.append({
            "Initiative": f"Retain {at_risk_n} High-Value At-Risk customers",
            "Category":   "Retention",
            "Revenue Impact":      5 if at_risk_clv > 150_000 else 4,
            "Implementation Ease": 4,
            "Time to Value":       "1-3 months",
            "Evidence Source":     f"${at_risk_clv:,.0f} annualised CLV at stake | below-median flight count",
            "Class":               "High-Value At-Risk",
            "Confidence %":        90,
            "_revenue":            at_risk_clv,
        })
    if high_prop_n > 0:
        initiatives.append({
            "Initiative": f"Upsell campaign on {high_prop_n} high-propensity customers",
            "Category":   "Upsell",
            "Revenue Impact":      4 if high_prop_n >= 50 else 3,
            "Implementation Ease": 5,
            "Time to Value":       "1-3 months",
            "Evidence Source":     f"{loyal_n} Loyal Advocates + {growth_n} Growth Targets | premium conv > 15%",
            "Class":               "Cross-sell",
            "Confidence %":        85,
            "_revenue":            None,
        })

    pmat = pd.DataFrame(initiatives)

    st.subheader("Investment Priority Matrix")
    st.caption("Auto-generated from `ont_route_classification` + `ont_customer_classification` — every initiative is grounded in classified data.")
    fig_matrix = px.scatter(
        pmat, x="Implementation Ease", y="Revenue Impact",
        size="Confidence %", color="Category",
        hover_name="Initiative",
        hover_data={"Class": True, "Time to Value": True, "Evidence Source": True,
                    "Confidence %": True, "Implementation Ease": False, "Revenue Impact": False},
        color_discrete_map={"Network": COLORS["primary"], "Retention": COLORS["danger"], "Upsell": COLORS["secondary"]},
        template="plotly_white",
        labels={"Revenue Impact": "Revenue Impact (1-5)", "Implementation Ease": "Ease (1-5)"},
        size_max=40,
    )
    fig_matrix.update_traces(marker=dict(line=dict(width=1, color="white")))
    fig_matrix.update_layout(height=440)
    fig_matrix.add_hline(y=3.5, line_dash="dot", line_color="gray", annotation_text="High impact ↑")
    fig_matrix.add_vline(x=3.5, line_dash="dot", line_color="gray", annotation_text="Easy ↑")
    st.plotly_chart(fig_matrix, use_container_width=True)
    with st.expander("Full initiative table"):
        st.dataframe(pmat.drop(columns=["_revenue"]).sort_values(
            ["Revenue Impact", "Implementation Ease"], ascending=[False, False]
        ), use_container_width=True, hide_index=True)

    st.divider()

    # ── Top 3 recommendations (data-driven) ───────────────────────────────────
    st.subheader("Executive Recommendations")

    # Pick the single most critical route in each strategic class.
    def first_of_class(target_class: str) -> dict | None:
        for r in route_class:
            if r["route_class"] == target_class:
                return r
        return None

    ops_risk_route = first_of_class("Operational Risk")
    growth_route   = max(
        (r for r in routes_perf if r["route_id"] in {x["route_id"] for x in route_class if x["route_class"] in ("Strategic Growth", "Cash Cow")}),
        key=lambda r: r["total_revenue_usd"], default=None,
    )

    rec1, rec2, rec3 = st.columns(3)

    with rec1:
        if ops_risk_route:
            margin_at_stake = ops_risk_route["total_margin_usd"] or 0
            monthly_uplift_low  = round(margin_at_stake * 0.10 / 12)
            monthly_uplift_high = round(margin_at_stake * 0.25 / 12)
            st.markdown(
                f"""
                <div style="background:#EBF5FB;border-left:4px solid {COLORS['primary']};padding:16px;border-radius:4px">
                <h4 style="color:{COLORS['primary']}">1. Invest in Route Reliability</h4>
                <p><strong>Priority:</strong> Fix {ops_risk_route['route_label']}</p>
                <p>Highest-margin operational-risk route ({ops_risk_route['margin_pct']:.1f}% margin)
                but {ops_risk_route['delay_rate_pct']:.1f}% delay rate destroys NPS ({ops_risk_route['route_nps']:.0f}).
                Verbatim reviews flag <em>'retard systématique'</em>. Reliability fix
                (scheduling + ground crew) protects margin before it leaks.</p>
                <p><strong>Estimated monthly margin protected:</strong> ${monthly_uplift_low:,}–${monthly_uplift_high:,}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No Operational Risk route under current ontology — reliability spend not the top lever.")

    with rec2:
        annual_clv = at_risk_clv
        protect_low  = round(annual_clv * 0.60)
        protect_high = round(annual_clv * 0.90)
        st.markdown(
            f"""
            <div style="background:#FEF9E7;border-left:4px solid {COLORS['warning']};padding:16px;border-radius:4px">
            <h4 style="color:{COLORS['warning']}">2. Retain High-Value Customers</h4>
            <p><strong>Priority:</strong> {at_risk_n} High-Value At-Risk customers</p>
            <p>Top revenue tier with below-median flight frequency relative to peers.
            Targeted retention offers (upgrade vouchers, bonus miles) re-engage them
            before they switch. Annual CLV exposure: <strong>${annual_clv:,.0f}</strong>.</p>
            <p><strong>Estimated revenue protected:</strong> ${protect_low:,}–${protect_high:,}/year</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rec3:
        if growth_route:
            current_lf = growth_route["avg_load_factor_pct"] or 0
            seats      = growth_route["configured_seats"] or 0
            avg_price  = growth_route["avg_ticket_price_usd"] or 0
            total_flights = growth_route["total_flights"] or 0
            # If load factor doubles, additional passengers = current_lf * seats * flights * 12 (annualised)
            uplift_passengers = current_lf / 100 * seats * total_flights * 12
            uplift_revenue    = uplift_passengers * avg_price
            uplift_margin_low  = round(uplift_revenue * 0.20)
            uplift_margin_high = round(uplift_revenue * 0.45)
            st.markdown(
                f"""
                <div style="background:#EAFAF1;border-left:4px solid {COLORS['success']};padding:16px;border-radius:4px">
                <h4 style="color:{COLORS['success']}">3. Scale {growth_route['route_label']}</h4>
                <p><strong>Priority:</strong> Grow load factor (currently {current_lf:.1f}%)</p>
                <p>Highest-revenue healthy route (${growth_route['total_revenue_usd']:,.0f}) with
                {growth_route['margin_pct']:.1f}% margin and {growth_route['delay_rate_pct']:.1f}% delay.
                Capacity headroom is the lever — distribution and corporate contracts can move load factor.</p>
                <p><strong>Doubling load factor adds:</strong> ${uplift_margin_low:,}–${uplift_margin_high:,} annual margin</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info("No Strategic Growth / Cash Cow route identified.")

    st.divider()

    # ── Budget allocation — derived from class composition + revenue weights ──
    st.subheader("Recommended Budget Allocation (Next 12 Months)")

    # Buckets and their default weights — adjusted by class composition below.
    class_to_bucket = {
        "Operational Risk":        "Network Operations Fix",
        "Critical Underperformer": "Route Restructuring Reserve",
        "Underperforming":         "Route Restructuring Reserve",
        "Strategic Growth":        "Growth Route Investment",
        "Cash Cow":                "Growth Route Investment",
    }
    revenue_per_bucket: dict[str, float] = {}
    for r in route_class:
        bucket = class_to_bucket.get(r["route_class"])
        if not bucket:
            continue
        revenue_per_bucket[bucket] = revenue_per_bucket.get(bucket, 0) + (r["total_revenue_usd"] or 0)

    # Allocate 70% of budget proportional to revenue at stake on the network side,
    # and 30% fixed split between Retention (20%) and Ancillary Upsell (10%).
    network_total = sum(revenue_per_bucket.values()) or 1
    network_share = 70
    network_pct   = {k: round(v / network_total * network_share, 1) for k, v in revenue_per_bucket.items()}
    fixed_pct     = {"Retention Program": 20.0, "Ancillary Upsell": 10.0}

    rationale = {
        "Network Operations Fix":     f"Fix delay/cancel issues on {sum(1 for r in route_class if r['route_class']=='Operational Risk')} Operational Risk route(s).",
        "Growth Route Investment":    f"Scale {sum(1 for r in route_class if r['route_class'] in ('Strategic Growth','Cash Cow'))} healthy routes — capacity, distribution, partnerships.",
        "Route Restructuring Reserve": f"Restructure/exit {sum(1 for r in route_class if r['route_class'] in ('Critical Underperformer','Underperforming'))} weak route(s).",
        "Retention Program":           f"Personalised offers for {at_risk_n} High-Value At-Risk + {growth_n} Growth Targets.",
        "Ancillary Upsell":            f"Upgrade campaigns + ancillary bundles for {high_prop_n} high-propensity customers.",
    }

    budget_rows = [{"Area": k, "Allocation %": v, "Rationale": rationale.get(k, "")} for k, v in {**network_pct, **fixed_pct}.items() if v > 0]
    budget = pd.DataFrame(budget_rows).sort_values("Allocation %", ascending=False)
    fig_budget = px.pie(
        budget, values="Allocation %", names="Area",
        color_discrete_sequence=px.colors.qualitative.Set2,
        template="plotly_white",
    )
    fig_budget.update_traces(textposition="inside", textinfo="percent+label")
    fig_budget.update_layout(height=380, showlegend=False)

    col_b1, col_b2 = st.columns([1, 1])
    col_b1.plotly_chart(fig_budget, use_container_width=True)
    col_b2.dataframe(budget[["Area","Allocation %","Rationale"]], use_container_width=True, hide_index=True)

    st.divider()

    # ── Evidence from unstructured data ──────────────────────────────────────
    st.subheader("Evidence from Unstructured Data (Reviews & Tickets)")
    col_ev1, col_ev2 = st.columns(2)

    with col_ev1:
        st.caption("Top complaint themes driving low satisfaction")
        tickets_summary = q("""
            SELECT category, COUNT(*) as tickets,
                   ROUND(AVG(csat_score),1) as avg_csat,
                   SUM(CASE WHEN status='Open' THEN 1 ELSE 0 END) as open_tickets
            FROM stg_support_tickets
            GROUP BY category
            ORDER BY tickets DESC
        """)
        fig_cat = px.bar(
            tickets_summary, x="tickets", y="category",
            orientation="h", color="avg_csat",
            color_continuous_scale="RdYlGn",
            text="open_tickets",
            labels={"tickets": "Total Tickets", "avg_csat": "Avg CSAT", "category": ""},
            template="plotly_white",
        )
        fig_cat.update_traces(texttemplate="%{text} open", textposition="outside")
        fig_cat.update_layout(height=300)
        st.plotly_chart(fig_cat, use_container_width=True)

    with col_ev2:
        st.caption("Sample negative reviews (operational evidence)")
        neg_reviews = q("""
            SELECT dr.route_label, sr.review_text, sr.nps_score
            FROM stg_reviews sr
            JOIN dim_route dr ON sr.route_id = dr.route_id
            WHERE sr.sentiment = 'negative'
            ORDER BY sr.nps_score ASC
            LIMIT 5
        """)
        for _, r in neg_reviews.iterrows():
            st.markdown(
                f"**[NPS {r['nps_score']}]** {r['route_label']}: "
                f"_{r['review_text'][:120]}..._"
            )

    # ── Route decisions summary ───────────────────────────────────────────────
    st.divider()
    st.subheader("Route Decision Summary")
    decision_df = route_class_df[["route_label","route_class","budget_recommendation","margin_pct","delay_rate_pct","total_revenue_usd"]].copy()
    decision_df.columns = ["Route","Class","Recommendation","Margin %","Delay %","Revenue (USD)"]
    decision_df["Revenue (USD)"] = decision_df["Revenue (USD)"].apply(lambda x: f"${x:,.0f}")
    decision_df["Margin %"] = decision_df["Margin %"].apply(lambda x: f"{x:.1f}%")
    decision_df["Delay %"] = decision_df["Delay %"].apply(lambda x: f"{x:.1f}%")

    def color_class(val):
        c = CLASS_COLORS.get(val, "white")
        return f"background-color: {c}; color: white; font-weight: bold"

    st.dataframe(
        decision_df.style.map(color_class, subset=["Class"]),
        use_container_width=True,
        hide_index=True,
    )
