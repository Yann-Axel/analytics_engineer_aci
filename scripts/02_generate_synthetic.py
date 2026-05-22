"""
Generate synthetic enrichment data for the Air Côte d'Ivoire analytics challenge.

Six datasets are produced. Two of them (customer_reviews, support_tickets) are
unstructured and intentionally correlated with operational signals from the
starter data so downstream models surface coherent themes per route.

Datasets:
  - aircraft_fleet     : fleet specs, fuel burn, ownership
  - fare_details       : operating cost, fuel cost, breakeven load factor
  - loyalty_activity   : points earned/redeemed, tier upgrades
  - customer_reviews   : NPS + verbatim text (unstructured), bilingual fr/en
  - support_tickets    : complaint logs, weighted by route operational stress
  - competitor_context : monthly competitor price benchmarks per route

Design notes
------------
* All dates are bounded relative to REFERENCE_DATE (see aci_config.py) so the
  synthetic data is reproducible and stable across calendar time.
* Support ticket route assignment is weighted by each route's delay rate and
  cancellation rate. R001's high delay rate therefore drives more "Flight
  Delay" tickets on R001 than on R002 — the unstructured evidence aligns with
  the structured KPIs.
* Customers receiving tickets are sampled from the set of customers who
  actually flew that route (via bookings), not random customers.
* Reviews are deepened with 25+ templates per sentiment plus per-route issue
  fragments to avoid duplication in downstream embedding search.
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import numpy as np
from faker import Faker

sys.path.insert(0, str(Path(__file__).parent.parent))
from aci_config import (
    DB_PATH,
    PROJECT_ROOT,
    RANDOM_SEED,
    REFERENCE_DATE,
    FUEL_PRICE_USD_PER_KG,
    CREW_COST_USD_PER_BLOCK_HOUR,
    AIRPORT_FEE_FIXED_USD,
    AIRPORT_FEE_PER_KM,
)

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)
fake = Faker(["fr_FR", "en_US"])
fake.seed_instance(RANDOM_SEED)

SYNTH_DIR = PROJECT_ROOT / "data" / "synthetic"
SYNTH_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_DT = datetime.strptime(REFERENCE_DATE, "%Y-%m-%d").date()
TICKET_WINDOW_START = REFERENCE_DT - timedelta(days=120)
LOYALTY_WINDOW_START = REFERENCE_DT - timedelta(days=540)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def random_date_between(start, end):
    delta_days = (end - start).days
    return start + timedelta(days=random.randint(0, max(delta_days, 0)))


con = duckdb.connect(str(DB_PATH))

routes_df = con.execute("SELECT * FROM raw_routes").df()
flights_df = con.execute("SELECT * FROM raw_flights").df()
customers_df = con.execute("SELECT * FROM raw_customers").df()
bookings_df = con.execute("SELECT * FROM raw_bookings").df()

route_ids = routes_df["route_id"].tolist()

# Operational stress per route: delay rate (>15 min) + cancellation rate.
# Used downstream to skew support tickets toward stressed routes.
flights_df["_delay_min"] = flights_df["delay_min"].fillna(0).astype(int)
route_ops = (
    flights_df.assign(
        is_delayed=lambda d: (d["_delay_min"] > 15).astype(int),
        is_cancelled=lambda d: (d["flight_status"] == "Cancelled").astype(int),
    )
    .groupby("route_id")
    .agg(
        total_flights=("flight_id", "count"),
        delay_rate=("is_delayed", "mean"),
        cancel_rate=("is_cancelled", "mean"),
        avg_delay=("_delay_min", "mean"),
    )
    .reset_index()
)
ops_lookup = route_ops.set_index("route_id").to_dict("index")


# ──────────────────────────────────────────────────────────────────────────────
# 1. AIRCRAFT FLEET
# ──────────────────────────────────────────────────────────────────────────────
FLEET = [
    {"aircraft_type": "A319", "manufacturer": "Airbus", "seats": 122,
     "fuel_burn_kg_per_h": 2400, "max_range_km": 6850, "age_years": 8,
     "ownership": "Owned"},
    {"aircraft_type": "A320", "manufacturer": "Airbus", "seats": 150,
     "fuel_burn_kg_per_h": 2600, "max_range_km": 6100, "age_years": 5,
     "ownership": "Leased"},
    {"aircraft_type": "A320neo", "manufacturer": "Airbus", "seats": 165,
     "fuel_burn_kg_per_h": 2100, "max_range_km": 6300, "age_years": 2,
     "ownership": "Leased"},
    {"aircraft_type": "A330-900neo", "manufacturer": "Airbus", "seats": 290,
     "fuel_burn_kg_per_h": 5800, "max_range_km": 13334, "age_years": 1,
     "ownership": "Leased"},
    {"aircraft_type": "ATR72", "manufacturer": "ATR", "seats": 68,
     "fuel_burn_kg_per_h": 1100, "max_range_km": 1528, "age_years": 6,
     "ownership": "Owned"},
]
TAIL_COUNT = {"A319": 3, "A320": 2, "A320neo": 2, "A330-900neo": 2, "ATR72": 3}

aircraft_rows = []
tail_num = 1
for spec in FLEET:
    for _ in range(TAIL_COUNT[spec["aircraft_type"]]):
        aircraft_rows.append({
            "tail_number": f"TU-{tail_num:03d}",
            **spec,
            "avg_utilization_h_per_day": round(random.uniform(8, 14), 1),
        })
        tail_num += 1

write_csv(SYNTH_DIR / "aircraft_fleet.csv", aircraft_rows, list(aircraft_rows[0].keys()))
print(f"  aircraft_fleet: {len(aircraft_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# 2. FARE DETAILS (per-route operating economics)
# ──────────────────────────────────────────────────────────────────────────────
fare_details_rows = []
for _, r in routes_df.iterrows():
    distance = int(r["distance_km"])
    block_h = int(r["block_time_min"]) / 60

    if r["route_type"] == "Domestic" and distance < 600:
        ac_type, seats, burn = "ATR72", 68, 1100
    elif r["route_type"] == "International" and distance > 5000:
        ac_type, seats, burn = "A330-900neo", 290, 5800
    elif r["route_type"] == "International" and distance > 2000:
        ac_type, seats, burn = "A320neo", 165, 2100
    else:
        ac_type, seats, burn = "A320", 150, 2600

    fuel_cost = round(burn * block_h * FUEL_PRICE_USD_PER_KG, 2)
    crew_cost = round(block_h * CREW_COST_USD_PER_BLOCK_HOUR, 2)
    airport_fees = round(distance * AIRPORT_FEE_PER_KM + AIRPORT_FEE_FIXED_USD, 2)
    total_op_cost = round(fuel_cost + crew_cost + airport_fees, 2)
    breakeven_lf = round(total_op_cost / (seats * (distance * 0.09 + 50)) * 100, 1)
    breakeven_lf = min(breakeven_lf, 95.0)

    fare_details_rows.append({
        "route_id": r["route_id"],
        "aircraft_type_assigned": ac_type,
        "seat_capacity": seats,
        "fuel_cost_usd": fuel_cost,
        "crew_cost_usd": crew_cost,
        "airport_fees_usd": airport_fees,
        "total_operating_cost_usd": total_op_cost,
        "breakeven_load_factor_pct": breakeven_lf,
        "avg_competitor_price_usd": round(distance * 0.10 + 80 + random.uniform(-30, 50), 2),
    })

write_csv(SYNTH_DIR / "fare_details.csv", fare_details_rows, list(fare_details_rows[0].keys()))
print(f"  fare_details: {len(fare_details_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# 3. LOYALTY ACTIVITY
# ──────────────────────────────────────────────────────────────────────────────
TIER_BALANCE_RANGE = {
    "Bronze":   (1, 800),
    "Silver":   (800, 3000),
    "Gold":     (3000, 8000),
    "Platinum": (8000, 20000),
}

loyalty_rows = []
act_id = 1
for cust in customers_df.itertuples():
    tier = cust.loyalty_tier if cust.loyalty_tier in TIER_BALANCE_RANGE else "Bronze"
    lo, hi = TIER_BALANCE_RANGE[tier]
    balance = random.randint(lo, hi)
    n_events = random.randint(2, 12)

    for _ in range(n_events):
        evt_date = random_date_between(LOYALTY_WINDOW_START, REFERENCE_DT)
        evt_type = random.choices(
            ["earn_flight", "earn_bonus", "redeem_upgrade", "redeem_voucher", "tier_upgrade"],
            weights=[50, 15, 15, 15, 5],
        )[0]
        if evt_type.startswith("earn"):
            pts = random.randint(100, 2000)
        elif evt_type == "tier_upgrade":
            pts = 0
        else:
            pts = -random.randint(200, 1500)

        balance = max(0, balance + pts)
        loyalty_rows.append({
            "activity_id": f"LOY{act_id:06d}",
            "customer_id": cust.customer_id,
            "activity_date": str(evt_date),
            "activity_type": evt_type,
            "points_change": pts,
            "running_balance": balance,
            "tier_after": tier,
            "channel": random.choice(["App", "Web", "Agent", "Kiosk"]),
        })
        act_id += 1

write_csv(SYNTH_DIR / "loyalty_activity.csv", loyalty_rows, list(loyalty_rows[0].keys()))
print(f"  loyalty_activity: {len(loyalty_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# 4. CUSTOMER REVIEWS (unstructured — NPS + verbatim, fr/en)
# ──────────────────────────────────────────────────────────────────────────────
REVIEW_TEMPLATES_FR = {
    "positive": [
        "Vol excellent, équipage très professionnel. Je reviendrai certainement.",
        "Service impeccable, départ à l'heure. Bravo à l'équipage d'Air Côte d'Ivoire.",
        "Très bon vol, siège confortable et repas savoureux. Recommandé sans hésiter.",
        "Embarquement fluide, équipage souriant, vol parfait du début à la fin.",
        "Excellente compagnie. Les hôtesses étaient attentionnées et le pilote très rassurant.",
        "Surclassement gratuit en Business, expérience inoubliable. Merci ACI !",
        "Vol agréable, divertissement à bord varié. On se sent vraiment bien traité.",
        "Le rapport qualité-prix sur cette destination est imbattable. Continuez ainsi.",
        "Personnel chaleureux, accueil africain authentique. Je recommande à 100%.",
        "Repas africain délicieux à bord, vraie touche locale appréciable.",
        "Voyage en famille parfaitement géré, attention particulière aux enfants.",
        "Vol matinal très ponctuel, idéal pour les voyages d'affaires.",
        "Le nouveau A330 est superbe, sièges confortables même en éco.",
    ],
    "neutral": [
        "Vol correct, rien d'exceptionnel. Le service est moyen.",
        "Départ légèrement en retard mais arrivée à l'heure. Acceptable.",
        "Avion propre, équipage poli sans plus. Vol sans incident.",
        "Repas basique mais consommable. Le siège était convenable.",
        "Embarquement un peu long mais le vol s'est bien déroulé ensuite.",
        "Service standard pour le prix payé. Pas de quoi se plaindre.",
        "Vol sans surprise, ni bonne ni mauvaise. Je referai si nécessaire.",
        "Personnel correct, divertissement limité. Acceptable pour la durée.",
        "Le check-in en ligne fonctionne bien, l'embarquement aussi.",
        "Climatisation un peu froide mais des couvertures étaient disponibles.",
    ],
    "negative": [
        "Retard de 2 heures sans explication. Service clientèle décevant.",
        "Bagages perdus et aucune aide de l'équipe au sol. Très déçu.",
        "Vol annulé et rebooking chaotique. Communication désastreuse.",
        "Siège cassé, repas servi froid, service lent. Billet trop cher pour cette qualité.",
        "Personnel à bord peu aimable, on a l'impression de déranger.",
        "Embarquement chaotique, file d'attente interminable au comptoir.",
        "Wi-Fi annoncé mais inopérant pendant tout le vol. Décevant.",
        "Avion vieillissant, climatisation défaillante, sièges abîmés.",
        "Encore un retard sur cette ligne, ça devient systématique.",
        "Repas immangeable, je n'ai pas pu finir mon plateau.",
        "Réclamation pour bagage abîmé ignorée depuis 3 semaines.",
        "Aucune assistance pour ma correspondance ratée à cause du retard.",
        "Mes points fidélité n'ont pas été crédités après ce vol. Service après-vente injoignable.",
        "Comparé à Ethiopian ou Air France, le niveau de service n'y est pas.",
    ],
}

REVIEW_TEMPLATES_EN = {
    "positive": [
        "Excellent flight from check-in to landing. Staff were very helpful and friendly.",
        "On-time departure and smooth landing. Great value for money on this route.",
        "The cabin crew was outstanding. Very attentive and professional.",
        "Clean aircraft, friendly staff. Will definitely book again.",
        "Smooth flight, great food options. The lounge access in Abidjan was a nice touch.",
        "Surprised by the quality on this regional flight. Pleasant experience overall.",
        "Crew handled a minor turbulence event calmly and professionally. Reassuring.",
        "Great connection between ABJ and CDG, comparable to European carriers.",
        "Loved the African hospitality on board. Felt welcomed throughout.",
        "Business cabin on the A330 is excellent value compared to competitors.",
        "Premium economy seat was worth every dollar on the long-haul.",
        "Booked through the app and everything worked seamlessly.",
    ],
    "neutral": [
        "The flight was okay. Nothing special but nothing bad either.",
        "Seat was a bit cramped but the crew was friendly. Average experience.",
        "Food could be better. Flight was on time though.",
        "Decent flight overall. The check-in process was a little slow.",
        "Standard regional service. Aircraft was clean enough.",
        "Boarding took longer than expected but the flight itself was fine.",
        "Entertainment options limited on this aircraft type. Otherwise acceptable.",
        "Lounge in CDG was crowded but the flight crew was helpful.",
    ],
    "negative": [
        "Flight delayed 3 hours. No communication from staff. Very frustrated.",
        "Lost my baggage and still waiting for it. Unacceptable service.",
        "Terrible experience at check-in. Long queues and unhelpful staff.",
        "The aircraft was dirty. Seat wouldn't recline. Disappointed.",
        "Cancelled with only 2 hours notice. No rebooking offered, no hotel.",
        "Crew was rude when I asked about my missed connection.",
        "Meal was inedible. Vegetarian option was just a piece of bread.",
        "Multiple delays on this route this year. Reliability is a real issue.",
        "Compensation claim filed two months ago, still no response.",
        "Inflight Wi-Fi did not work despite being charged for it.",
        "Frequent flyer points still not credited after multiple complaints.",
        "Cabin was overheated for the entire flight. No working AC.",
    ],
}

ROUTE_ISSUES_FR = {
    "R001": "retard systématique le matin sur la rotation ABJ-Bouaké",
    "R002": "siège inconfortable sur l'ATR pour cette durée de vol",
    "R005": "bagages fréquemment perdus sur la liaison Dakar",
    "R006": "encombrement chronique à Lagos, créneaux non respectés",
    "R007": "turbulences fréquentes et service perturbé",
    "R008": "annulations répétées sur la ligne Ouagadougou",
    "R009": "retards liés aux créneaux horaires à Paris CDG",
    "R011": "manque de connexions cohérentes vers l'est africain",
}
ROUTE_ISSUES_EN = {
    "R001": "systematic morning delays on the Bouaké rotation",
    "R002": "uncomfortable ATR seat for this flight length",
    "R005": "baggage frequently mishandled on the Dakar line",
    "R006": "Lagos congestion, schedule slots routinely missed",
    "R007": "frequent turbulence and disrupted service",
    "R008": "repeated cancellations on the Ouagadougou route",
    "R009": "Paris CDG slot delays affecting connections",
    "R011": "lack of consistent eastward African connections",
}

# Reviews per flight: 1-6, weighted by load (higher load → more reviews).
# Sentiment biased by realized delay/cancellation.
reviews_rows = []
rev_id = 1
for flt in flights_df.itertuples():
    n_reviews = random.randint(1, 6)
    flight_status = flt.flight_status
    delay = int(flt._delay_min) if hasattr(flt, "_delay_min") else 0
    for _ in range(n_reviews):
        language = random.choices(["fr", "en"], weights=[60, 40])[0]
        templates = REVIEW_TEMPLATES_FR if language == "fr" else REVIEW_TEMPLATES_EN
        issues_map = ROUTE_ISSUES_FR if language == "fr" else ROUTE_ISSUES_EN

        if flight_status == "Cancelled":
            sentiment = "negative"
            nps = random.randint(0, 3)
        elif delay > 60:
            sentiment = random.choices(["negative", "neutral"], weights=[80, 20])[0]
            nps = random.randint(0, 5)
        elif delay > 15:
            sentiment = random.choices(["negative", "neutral", "positive"], weights=[55, 35, 10])[0]
            nps = random.randint(3, 7) if sentiment != "positive" else random.randint(7, 9)
        else:
            sentiment = random.choices(["positive", "neutral", "negative"], weights=[55, 30, 15])[0]
            if sentiment == "positive":
                nps = random.randint(8, 10)
            elif sentiment == "neutral":
                nps = random.randint(5, 8)
            else:
                nps = random.randint(2, 6)

        text = random.choice(templates[sentiment])
        if sentiment == "negative" and flt.route_id in issues_map and random.random() < 0.55:
            connector = "Problème récurrent : " if language == "fr" else "Recurring issue: "
            text = f"{text} {connector}{issues_map[flt.route_id]}."

        reviews_rows.append({
            "review_id": f"REV{rev_id:06d}",
            "flight_id": flt.flight_id,
            "route_id": flt.route_id,
            "review_date": str(flt.flight_date)[:10],
            "nps_score": nps,
            "sentiment": sentiment,
            "review_text": text,
            "language": language,
            "source": random.choice(["App", "Email Survey", "Web", "TripAdvisor"]),
        })
        rev_id += 1

write_csv(SYNTH_DIR / "customer_reviews.csv", reviews_rows, list(reviews_rows[0].keys()))
print(f"  customer_reviews: {len(reviews_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# 5. SUPPORT TICKETS (unstructured) — route-correlated
# ──────────────────────────────────────────────────────────────────────────────
TICKET_CATEGORIES = {
    "Baggage": [
        "Mes bagages n'ont pas été livrés à l'arrivée.",
        "Baggage damaged on arrival. Wheel broken and zipper torn.",
        "My suitcase arrived open and items were missing.",
        "Still waiting for delayed baggage from 3 days ago.",
        "Bagage cabine refusé à l'embarquement sans justification.",
        "Lost my hand luggage during boarding. Customer service unhelpful.",
        "Frais d'excédent bagage facturés deux fois sur ma carte.",
    ],
    "Flight Delay": [
        "Mon vol a été retardé de 4 heures. Aucun repas fourni.",
        "Flight delayed with no notification sent to passengers.",
        "Missed connecting flight due to Air CI delay. Need compensation.",
        "Vol retardé plusieurs fois sur ce mois. Inacceptable.",
        "3-hour tarmac delay with no air conditioning.",
        "Vol systématiquement en retard le matin sur cette ligne.",
        "Aucune information donnée pendant l'attente prolongée en salle d'embarquement.",
    ],
    "Customer Service": [
        "Agent au sol très impoli et peu serviable.",
        "Phone support kept me on hold for 45 minutes.",
        "No response to my email sent 2 weeks ago.",
        "Le service clientèle en ligne est inexistant.",
        "Promise de rappel non tenue après ma plainte initiale.",
        "Twitter team responded but did not resolve the issue.",
    ],
    "Refund": [
        "Remboursement non reçu après annulation il y a 6 semaines.",
        "Requested refund 30 days ago. No update from the airline.",
        "Vol annulé par la compagnie mais pas de remboursement proposé.",
        "Voucher reçu au lieu du remboursement promis.",
        "Compensation EU261 demandée pour vol retardé, sans réponse.",
    ],
    "Booking Issue": [
        "Impossible de modifier ma réservation en ligne.",
        "Double-charged for seat selection. Please refund.",
        "Upgrade not applied despite payment confirmation.",
        "Erreur lors du paiement, deux billets émis.",
        "Application mobile bloque à l'étape de paiement.",
    ],
    "Onboard Experience": [
        "Repas de très mauvaise qualité sur le vol ABJ-CDG.",
        "Seat recline broken. Crew ignored my request.",
        "Air conditioning was too cold. No blankets available.",
        "Wi-Fi à bord facturé mais inopérant pendant tout le vol.",
        "Écran d'écran cassé, pas de divertissement disponible.",
        "Choice of vegetarian meals very limited compared to competitors.",
    ],
}

# Compute a per-route weight = base (volume) * stress multiplier.
# Stress multiplier is bounded so even healthy routes get some tickets.
def stress_multiplier(route_id: str) -> float:
    ops = ops_lookup.get(route_id, {"delay_rate": 0, "cancel_rate": 0})
    return 1.0 + 4.0 * ops["delay_rate"] + 6.0 * ops["cancel_rate"]

route_weights = {r: ops_lookup[r]["total_flights"] * stress_multiplier(r) for r in route_ids}
weight_sum = sum(route_weights.values())
route_pmf = {r: w / weight_sum for r, w in route_weights.items()}

# Per-route category weights — stressed routes get heavier weighting on
# operational categories (Flight Delay, Baggage, Refund).
def category_pmf_for(route_id: str) -> dict[str, float]:
    ops = ops_lookup.get(route_id, {"delay_rate": 0, "cancel_rate": 0})
    base = {
        "Baggage":            1.0,
        "Flight Delay":       1.0,
        "Customer Service":   1.0,
        "Refund":             0.6,
        "Booking Issue":      0.8,
        "Onboard Experience": 0.9,
    }
    base["Flight Delay"] += 4.0 * ops["delay_rate"]
    base["Refund"]       += 6.0 * ops["cancel_rate"]
    base["Baggage"]      += 1.5 * ops["delay_rate"]
    total = sum(base.values())
    return {k: v / total for k, v in base.items()}

# Build a customer-per-route lookup (only customers who actually flew that route).
bookings_with_routes = bookings_df.merge(
    flights_df[["flight_id", "route_id"]], on="flight_id", how="left"
)
customers_per_route = (
    bookings_with_routes.dropna(subset=["route_id"])
    .groupby("route_id")["customer_id"]
    .apply(lambda s: s.unique().tolist())
    .to_dict()
)

TICKET_COUNT = 1500
ticket_rows = []
tkt_id = 1
for _ in range(TICKET_COUNT):
    route_id = random.choices(list(route_pmf.keys()), weights=list(route_pmf.values()))[0]
    cat_pmf = category_pmf_for(route_id)
    category = random.choices(list(cat_pmf.keys()), weights=list(cat_pmf.values()))[0]

    description = random.choice(TICKET_CATEGORIES[category])

    eligible_customers = customers_per_route.get(route_id, [])
    cust_id = random.choice(eligible_customers) if eligible_customers else random.choice(customers_df["customer_id"].tolist())

    open_date = random_date_between(TICKET_WINDOW_START, REFERENCE_DT)
    resolved = random.random() > 0.25
    resolution_days = random.randint(1, 14) if resolved else None

    neg_cats = {"Baggage", "Flight Delay", "Customer Service", "Refund"}
    sentiment = "negative" if category in neg_cats else random.choice(["neutral", "negative"])

    ticket_rows.append({
        "ticket_id": f"TKT{tkt_id:06d}",
        "customer_id": cust_id,
        "route_id": route_id,
        "open_date": str(open_date),
        "category": category,
        "description": description,
        "sentiment": sentiment,
        "status": "Resolved" if resolved else "Open",
        "resolution_days": resolution_days if resolution_days else "",
        "csat_score": random.randint(1, 5) if resolved else "",
    })
    tkt_id += 1

write_csv(SYNTH_DIR / "support_tickets.csv", ticket_rows, list(ticket_rows[0].keys()))
print(f"  support_tickets: {len(ticket_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# 6. COMPETITOR CONTEXT (12 months of price benchmarks)
# ──────────────────────────────────────────────────────────────────────────────
COMPETITORS = {
    "R001": ["Starbow", "Fly540"],
    "R002": ["Starbow"],
    "R003": ["Ethiopian Airlines"],
    "R004": ["ASKY Airlines"],
    "R005": ["Kenya Airways", "Ethiopian Airlines"],
    "R006": ["ASKY Airlines", "Air Senegal"],
    "R007": ["Air Maroc", "Air Senegal"],
    "R008": ["Air France", "Brussels Airlines", "Turkish Airlines"],
    "R009": ["Air France", "Air Algérie"],
    "R010": ["Qatar Airways", "Emirates"],
    "R011": ["Ethiopian Airlines", "Kenya Airways"],
    "R012": ["Air France", "Corsair"],
}

competitor_rows = []
comp_id = 1
for route_id, comps in COMPETITORS.items():
    route_row = routes_df[routes_df["route_id"] == route_id].iloc[0]
    base_price = int(route_row["distance_km"]) * 0.10 + 80
    for month_offset in range(12):
        ref_month = datetime(2025, 1, 1) + timedelta(days=30 * month_offset)
        for comp in comps:
            aci_price = base_price * random.uniform(0.85, 1.15)
            comp_price = base_price * random.uniform(0.75, 1.25)
            competitor_rows.append({
                "comp_id": f"COMP{comp_id:05d}",
                "route_id": route_id,
                "month": ref_month.strftime("%Y-%m"),
                "competitor": comp,
                "competitor_avg_price_usd": round(comp_price, 2),
                "aci_avg_price_usd": round(aci_price, 2),
                "price_gap_usd": round(aci_price - comp_price, 2),
                "aci_cheaper": aci_price < comp_price,
            })
            comp_id += 1

write_csv(SYNTH_DIR / "competitor_context.csv", competitor_rows, list(competitor_rows[0].keys()))
print(f"  competitor_context: {len(competitor_rows)} rows")


# ──────────────────────────────────────────────────────────────────────────────
# Load all synthetic CSVs into DuckDB
# ──────────────────────────────────────────────────────────────────────────────
print("\nLoading synthetic tables into DuckDB...")
synth_tables = [
    "aircraft_fleet", "fare_details", "loyalty_activity",
    "customer_reviews", "support_tickets", "competitor_context",
]
for t in synth_tables:
    csv_path = SYNTH_DIR / f"{t}.csv"
    con.execute(f"DROP TABLE IF EXISTS synth_{t}")
    con.execute(f"""
        CREATE TABLE synth_{t} AS
        SELECT * FROM read_csv_auto('{csv_path.as_posix()}', header=true)
    """)
    count = con.execute(f"SELECT COUNT(*) FROM synth_{t}").fetchone()[0]
    print(f"  synth_{t}: {count} rows")

con.close()
print("\nSynthetic data generation complete.")
