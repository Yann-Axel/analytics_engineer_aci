import duckdb
con = duckdb.connect(r'c:\Analytic Engineer\air-cote-divoire\data\aci.duckdb')

print('Flight dates (all distinct months):')
print(con.execute("SELECT STRFTIME(flight_date, '%Y-%m') as ym, COUNT(*) as n FROM stg_flights GROUP BY ym ORDER BY ym").df().to_string())

print('\nAvg revenue per customer:')
print(con.execute('SELECT AVG(total_revenue_usd), MIN(total_revenue_usd), MAX(total_revenue_usd) FROM fact_customer_value').df().to_string())

print('\nLoad factor range:')
print(con.execute('SELECT MIN(load_factor_pct), AVG(load_factor_pct), MAX(load_factor_pct) FROM fact_flight').df().to_string())

print('\nBookings per customer (top 10):')
print(con.execute('SELECT customer_id, total_bookings, total_revenue_usd FROM fact_customer_value ORDER BY total_bookings DESC LIMIT 10').df().to_string())
