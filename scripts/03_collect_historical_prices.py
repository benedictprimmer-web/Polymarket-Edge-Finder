"""
Script 03: Collect Historical Prices
Fetches historical price data for markets using the CLOB API.
Reads market data from Script 01's output.
"""

import json
import os
import sys
import logging
from datetime import datetime, timezone
from api_client import PolymarketClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
INPUT_FILE = "data/markets_snapshot.json"
OUTPUT_FILE = "data/historical_prices.json"


def load_markets():
    """
    Load market data from Script 01's output.
    
    Returns:
        List of market dictionaries
    """
    if not os.path.exists(INPUT_FILE):
        logger.error(f"❌ Input file not found: {INPUT_FILE}")
        logger.error("Please run 01_discover_markets.py first.")
        sys.exit(1)
    
    try:
        with open(INPUT_FILE, 'r') as f:
            markets = json.load(f)
        logger.info(f"✅ Loaded {len(markets)} markets from {INPUT_FILE}")
        return markets
    except Exception as e:
        logger.error(f"❌ Error loading markets: {e}")
        sys.exit(1)


def collect_historical_prices(client: PolymarketClient, markets: list, max_markets: int = None) -> dict:
    """
    Collect historical price data for markets using CLOB API.
    
    Args:
        client: PolymarketClient instance
        markets: List of market dictionaries from Script 01
        max_markets: Optional limit on number of markets to process (for testing)
        
    Returns:
        Dictionary mapping market_id to historical price data
    """
    historical_data = {}
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Limit markets if specified
    if max_markets:
        markets = markets[:max_markets]
        logger.info(f"🔍 Collecting historical prices for {len(markets)} markets (limited to {max_markets})...")
    else:
        logger.info(f"🔍 Collecting historical prices for {len(markets)} markets...")
    
    for i, market in enumerate(markets, 1):
        market_id = market.get('market_id')
        question = market.get('question', 'Unknown')
        yes_token_id = market.get('yes_token_id')
        no_token_id = market.get('no_token_id')
        
        logger.info(f"[{i}/{len(markets)}] {question[:60]}...")
        
        # Skip markets without token IDs
        if not yes_token_id or not no_token_id:
            logger.warning(f"  ⚠️  Skipping: Missing token IDs")
            continue
        
        market_history = {
            'market_id': market_id,
            'question': question,
            'yes_token_id': yes_token_id,
            'no_token_id': no_token_id,
            'data_collected_at': timestamp,
            'yes_history': None,
            'no_history': None
        }
        
        # Fetch YES token price history
        logger.debug(f"  Fetching YES token history...")
        yes_history = client.get_prices_history(yes_token_id, interval="max", fidelity=60)
        if yes_history:
            market_history['yes_history'] = yes_history
            # Count data points if available
            history_data = yes_history.get('history', [])
            if isinstance(history_data, list):
                logger.info(f"  YES: {len(history_data)} historical data points")
            else:
                logger.info(f"  YES: Historical data retrieved")
        else:
            logger.info(f"  YES: No historical data available")
        
        # Fetch NO token price history
        logger.debug(f"  Fetching NO token history...")
        no_history = client.get_prices_history(no_token_id, interval="max", fidelity=60)
        if no_history:
            market_history['no_history'] = no_history
            # Count data points if available
            history_data = no_history.get('history', [])
            if isinstance(history_data, list):
                logger.info(f"  NO:  {len(history_data)} historical data points")
            else:
                logger.info(f"  NO:  Historical data retrieved")
        else:
            logger.info(f"  NO:  No historical data available")
        
        historical_data[market_id] = market_history
    
    logger.info(f"✅ Collected historical data for {len(historical_data)} markets")
    
    return historical_data


def save_historical_prices(data: dict):
    """
    Save historical price data to JSON file.
    
    Args:
        data: Dictionary of historical price data
    """
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    logger.info(f"📂 Saving historical prices to {OUTPUT_FILE}...")
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        logger.info("✅ Historical prices saved successfully!")
    except IOError as e:
        logger.error(f"❌ Error saving to file: {e}")
        sys.exit(1)


def main():
    """
    Main function to collect and save historical prices.
    """
    try:
        # Load markets from Script 01
        markets = load_markets()
        
        # Initialize API client with slightly longer rate limit for historical data
        client = PolymarketClient(rate_limit_delay=0.5)
        
        logger.info("\n⚠️  Note: Historical price collection can take a while for many markets.")
        logger.info("The CLOB API may not have historical data for all markets.")
        logger.info("New markets may have limited or no historical data.\n")
        
        # Collect historical prices
        # For testing, you can limit the number of markets:
        # historical_data = collect_historical_prices(client, markets, max_markets=10)
        historical_data = collect_historical_prices(client, markets)
        
        if historical_data:
            # Save to file
            save_historical_prices(historical_data)
            
            # Display summary
            logger.info("\n📊 Summary:")
            logger.info(f"  Markets processed: {len(markets)}")
            logger.info(f"  Historical data collected: {len(historical_data)}")
            
            # Count markets with data
            markets_with_yes_data = sum(1 for m in historical_data.values() if m['yes_history'])
            markets_with_no_data = sum(1 for m in historical_data.values() if m['no_history'])
            
            logger.info(f"  Markets with YES history: {markets_with_yes_data}")
            logger.info(f"  Markets with NO history: {markets_with_no_data}")
        else:
            logger.warning("❌ No historical data collected.")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
