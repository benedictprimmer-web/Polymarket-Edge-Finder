import requests
import json
import time
from datetime import datetime, timedelta

# Set the base URL for Polymarket CLOB API
base_url = 'https://api.polymarket.com/v1/'

# Function to fetch historical price data for a specific market

def fetch_historical_prices(market_id):
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=30)
    historical_prices = []

    while start_time < end_time:
        response = requests.get(f"{base_url}market/{market_id}/prices?start={int(start_time.timestamp())}&end={int(end_time.timestamp())}")
        if response.status_code == 200:
            data = response.json()
            hourly_snapshots = data.get('prices', [])
            historical_prices.extend(hourly_snapshots)
        time.sleep(1)  # To avoid rate limiting
        start_time += timedelta(hours=1)  # Move to the next hour

    return historical_prices

# Main function to collect all market data

def collect_all_market_data():
    # Fetch market IDs (replace with actual market fetching logic)
    market_ids = ['market_id_1', 'market_id_2']  # Placeholder IDs
    all_historical_data = {}

    for market_id in market_ids:
        print(f"Fetching data for market: {market_id}")
        historical_prices = fetch_historical_prices(market_id)
        all_historical_data[market_id] = historical_prices

    return all_historical_data

# Entry point
data = collect_all_market_data()

# Save the data to a JSON file
with open('data/historical_prices.json', 'w') as f:
    json.dump(data, f, indent=4)