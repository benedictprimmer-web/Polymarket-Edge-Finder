import requests
import json

# Connect to Polymarket Gamma API
url = 'https://api.polymarket.com/gamma/v1/markets'
response = requests.get(url)

if response.status_code == 200:
    markets = response.json()['markets']
    market_metadata = []

    # Extract relevant metadata from the open markets
    for market in markets:
        if market['isOpen']:
            metadata = {
                'question': market['question'],
                'token_ids': market['outcomeTokenIds'],
                'market_id': market['id'],
                'market_url': market['url'],
            }
            market_metadata.append(metadata)

    # Save the market metadata to a JSON file
    with open('data/markets_snapshot.json', 'w') as f:
        json.dump(market_metadata, f, indent=4)
else:
    print(f"Error fetching markets: {response.status_code}")
