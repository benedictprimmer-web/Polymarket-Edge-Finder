"""
Script 03: Collect Historical Prices
Fetches historical price data for markets using the CLOB API.
Reads market data from Script 01's output.
"""

import json
import os
import sys
import logging
import argparse
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


def filter_markets(markets: list) -> tuple:
    """
    Filter markets to only include active markets with liquidity and valid token IDs.
    
    Criteria:
    1. Not closed (state != 'closed' or closed field is not True)
    2. Has valid token IDs (yes_token_id and no_token_id are present and not empty)
    3. Has liquidity (liquidity is present, not null, not zero, and not "0")
    
    Args:
        markets: List of market dictionaries
        
    Returns:
        Tuple of (filtered_markets, skip_counts) where skip_counts is a dict with reasons
    """
    filtered = []
    skip_counts = {
        'closed': 0,
        'no_token_ids': 0,
        'no_liquidity': 0
    }
    
    for market in markets:
        # Check 1: Not closed
        state = market.get('state', '').lower()
        closed = market.get('closed', False)
        if state == 'closed' or closed:
            skip_counts['closed'] += 1
            continue
        
        # Check 2: Has valid token IDs
        yes_token_id = market.get('yes_token_id')
        no_token_id = market.get('no_token_id')
        if not yes_token_id or not no_token_id or yes_token_id == '' or no_token_id == '':
            skip_counts['no_token_ids'] += 1
            continue
        
        # Check 3: Has liquidity
        liquidity = market.get('liquidity')
        if liquidity is None or liquidity == 0 or liquidity == "0" or liquidity == '':
            skip_counts['no_liquidity'] += 1
            continue
        
        # Convert liquidity to float to check if it's effectively zero
        try:
            liq_val = float(liquidity)
            if liq_val == 0:
                skip_counts['no_liquidity'] += 1
                continue
        except (ValueError, TypeError):
            skip_counts['no_liquidity'] += 1
            continue
        
        # Market passed all filters
        filtered.append(market)
    
    return filtered, skip_counts


def collect_historical_prices(client: PolymarketClient, markets: list) -> dict:
    """
    Collect historical price data for markets using CLOB API.
    
    Args:
        client: PolymarketClient instance
        markets: List of market dictionaries from Script 01
        
    Returns:
        Dictionary mapping market_id to historical price data
    """
    historical_data = {}
    timestamp = datetime.now(timezone.utc).isoformat()
    
    logger.info(f"🔍 Collecting historical prices for {len(markets)} markets...")
    
    for i, market in enumerate(markets, 1):
        market_id = market.get('market_id')
        question = market.get('question', 'Unknown')
        yes_token_id = market.get('yes_token_id')
        no_token_id = market.get('no_token_id')
        
        logger.info(f"[{i}/{len(markets)}] {question[:60]}...")
        
        # Skip markets without token IDs (should not happen after filtering, but defensive check)
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
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Collect historical prices for Polymarket markets',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit the number of markets to process (useful for testing)'
    )
    args = parser.parse_args()
    
    try:
        # Load markets from Script 01
        all_markets = load_markets()
        
        # Filter markets to only include active ones with liquidity and token IDs
        markets, skip_counts = filter_markets(all_markets)
        
        # Log filtering results
        logger.info("\n📊 Market Filtering Summary:")
        logger.info(f"  Total markets loaded: {len(all_markets)}")
        logger.info(f"  Markets passed filter: {len(markets)}")
        logger.info(f"  Markets skipped: {len(all_markets) - len(markets)}")
        logger.info(f"    - Closed markets: {skip_counts['closed']}")
        logger.info(f"    - Markets with no token IDs: {skip_counts['no_token_ids']}")
        logger.info(f"    - Markets with no liquidity: {skip_counts['no_liquidity']}")
        
        # Apply limit if specified
        if args.limit and args.limit > 0:
            markets = markets[:args.limit]
            logger.info(f"\n🔢 Limiting to first {args.limit} markets for processing")
        
        if not markets:
            logger.warning("❌ No markets to process after filtering.")
            sys.exit(1)
        
        # Initialize API client with reduced rate limit
        client = PolymarketClient(rate_limit_delay=0.3)
        
        logger.info("\n⚠️  Note: Historical price collection can take a while for many markets.")
        logger.info("The CLOB API may not have historical data for all markets.")
        logger.info("New markets may have limited or no historical data.\n")
        
        # Collect historical prices
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
