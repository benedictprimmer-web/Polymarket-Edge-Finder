import requests
import json
from datetime import datetime

# Function to fetch current orderbook for each market

def fetch_orderbook(market_id):
    url = f'https://api.polymarket.com/v1/orderbook/{market_id}'
    response = requests.get(url)
    return response.json()

# Function to calculate mid-price and spread

def calculate_mid_price_and_spread(orderbook):
    best_bid = max(orderbook['bids'], key=lambda x: x['price'])
    best_ask = min(orderbook['asks'], key=lambda x: x['price'])
    mid_price = (best_bid['price'] + best_ask['price']) / 2
    spread = best_ask['price'] - best_bid['price']
    return mid_price, spread

# Main function to collect live prices

def collect_live_prices(market_ids):
    live_prices = {}
    for market_id in market_ids:
        orderbook = fetch_orderbook(market_id)
        mid_price, spread = calculate_mid_price_and_spread(orderbook)
        live_prices[market_id] = {'mid_price': mid_price, 'spread': spread, 'timestamp': datetime.utcnow().isoformat()}
    return live_prices

# List of market IDs to evaluate
market_ids = ['market1', 'market2']  # Replace with actual market IDs

# Collect live prices and save to data/live_prices.json
if __name__ == '__main__':
    prices = collect_live_prices(market_ids)
    with open('data/live_prices.json', 'w') as json_file:
        json.dump(prices, json_file, indent=4)
