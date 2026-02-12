import duckdb
import os

# Database file path
db_path = 'data/polymarket.duckdb'

# Create/connect to database
conn = duckdb.connect(db_path)

# Create tables with proper schemas.

# 1. Markets table
conn.execute("CREATE TABLE IF NOT EXISTS markets (market_id VARCHAR PRIMARY KEY, question VARCHAR, category VARCHAR, yes_token_id VARCHAR, no_token_id VARCHAR, market_url VARCHAR, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")

# 2. Price history table (stores hourly snapshots)
conn.execute("CREATE TABLE IF NOT EXISTS price_history (id INTEGER PRIMARY KEY DEFAULT nextval('seq_price_history'), market_id VARCHAR, token_id VARCHAR, timestamp TIMESTAMP, price DOUBLE, side VARCHAR, FOREIGN KEY (market_id) REFERENCES markets(market_id))")

# 3. Live prices table (current snapshot)
conn.execute("CREATE TABLE IF NOT EXISTS live_prices (market_id VARCHAR PRIMARY KEY, yes_price DOUBLE, no_price DOUBLE, yes_bid DOUBLE, yes_ask DOUBLE, no_bid DOUBLE, no_ask DOUBLE, yes_spread DOUBLE, no_spread DOUBLE, snapshot_time TIMESTAMP, FOREIGN KEY (market_id) REFERENCES markets(market_id))")

# 4. Edges table (detected trading opportunities)
conn.execute("CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY DEFAULT nextval('seq_edges'), market_id VARCHAR, edge_type VARCHAR, edge_percentage DOUBLE, recommendation VARCHAR, market_price DOUBLE, fair_price DOUBLE, confidence DOUBLE, detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY (market_id) REFERENCES markets(market_id))")

# Create sequences for auto-increment
conn.execute('CREATE SEQUENCE IF NOT EXISTS seq_price_history START 1')
conn.execute('CREATE SEQUENCE IF NOT EXISTS seq_edges START 1')

# Commit and close
conn.commit()
conn.close()

# Print confirmation
print(f"✅ Database initialized at {db_path}")
print("Tables created:")
print("  - markets")
print("  - price_history")
print("  - live_prices")
print("  - edges")