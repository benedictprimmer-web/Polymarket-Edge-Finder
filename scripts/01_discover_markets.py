import requests
import json
import os
import sys
from datetime import datetime, timezone
from urllib3.exceptions import InsecureRequestWarning
import warnings

# Suppress only the specific InsecureRequestWarning from urllib3
warnings.simplefilter('ignore', InsecureRequestWarning)

# Constants for API and file paths
GAMMA_API_URL = "https://gamma-api.polymarket.com/markets"
OUTPUT_FILE = "data/markets_snapshot.json"
MAX_RETRIES = 5
REQUEST_TIMEOUT = 10

def fetch_active_markets():
    """
    Fetch active markets from the Polymarket Gamma API.

    Returns:
        List[dict]: A list of active market metadata.
    """
    try:
        print("🔍 Discovering ACTIVE markets from Polymarket...")
        response = requests.get(GAMMA_API_URL, timeout=REQUEST_TIMEOUT, verify=False)  # Disable SSL warnings temporarily.
        response.raise_for_status()  # Check for HTTP request failures
        markets = response.json()
        
        print("✅ Data fetched successfully from Gamma API.")
        print("Processing active markets...")

        active_markets = [
            {
                'question': market.get('question'),
                'market_id': market.get('id'),
                'outcomes': market.get('outcomes', []),
                'ending_time': market.get('ending_time'),
                'category': market.get('category', 'unknown'),
                'state': market.get('state'),
                'url': f"https://polymarket.com/markets/{market.get('id')}",
                'volume': market.get('volume'),
                'data_updated_at': datetime.now(timezone.utc).isoformat(),
            }
            for market in markets if market.get('state') == 'active'
        ]
        
        print(f"  ✅ Found {len(markets)} total markets.")
        print(f"  📊 {len(active_markets)} ACTIVE markets after filtering by state.")

        return active_markets

    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}. Please check the API or network connection!")
        sys.exit(1)

def save_active_markets_to_file(markets):
    """
    Save active market metadata to a JSON file.
    Args:
        markets (list): A list of active market metadata.
    """
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    print(f"📂 Saving {len(markets)} active markets to {OUTPUT_FILE}...")
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(markets, f, indent=4)
        print("✅ Market data saved successfully!")
    except IOError as e:
        print(f"❌ Error occurred while trying to save to file: {e}")
        sys.exit(1)

def main():
    """
    Main function to fetch and save active markets data.
    """
    active_markets = fetch_active_markets()
    if active_markets:
        save_active_markets_to_file(active_markets)
        print("\nSample active markets:")
        for i, market in enumerate(active_markets[:5], 1):
            print(f"{i}. {market['question']} (Ends: {market['ending_time']})")
    else:
        print("❌ No active markets found to save.")
        sys.exit(1)

if __name__ == "__main__":
    main()
