"""
Script 02: Collect Live Prices
Fetches current orderbook data for markets using the CLOB API.
Reads market data from Script 01's output and calculates bid/ask/mid/spread.
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
OUTPUT_FILE = "data/live_prices.json"


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
    3. Token IDs are valid-looking (long numeric strings, not garbage like "[" or '"')
    4. Market hasn't ended yet (end_date_iso is in the future)
    5. Has liquidity (liquidity is present, not null, not zero, and not "0")
    
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
        if not yes_token_id or not no_token_id:
            skip_counts['no_token_ids'] += 1
            continue
        
        # Check 3: Token IDs are valid-looking (not garbage like "[" or '"')
        # Real Polymarket token IDs are long numeric strings (70+ characters)
        # Reject garbage values like "[", '"', or other short strings
        if len(str(yes_token_id)) < 10 or len(str(no_token_id)) < 10:
            skip_counts['no_token_ids'] += 1
            continue
        
        # Check 4: Market hasn't ended yet
        ending_time = market.get('ending_time') or market.get('end_date_iso')
        if ending_time:
            try:
                # Parse the ISO date string
                end_dt = datetime.fromisoformat(ending_time.replace('Z', '+00:00'))
                if end_dt < datetime.now(timezone.utc):
                    skip_counts['closed'] += 1  # Count as "closed" since they've ended
                    continue
            except (ValueError, TypeError):
                pass  # If we can't parse the date, don't skip
        
        # Check 5: Has liquidity (convert to float to check if it's effectively non-zero)
        liquidity = market.get('liquidity')
        if not liquidity:
            skip_counts['no_liquidity'] += 1
            continue
        
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


def parse_orderbook(orderbook: dict) -> dict:
    """
    Parse orderbook data to extract best bid, best ask, mid price, and spread.
    
    Args:
        orderbook: Orderbook dictionary with 'bids' and 'asks'
        
    Returns:
        Dictionary with best_bid, best_ask, mid_price, spread (or None values if empty)
    """
    result = {
        'best_bid': None,
        'best_ask': None,
        'mid_price': None,
        'spread': None
    }
    
    if not orderbook:
        return result
    
    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])
    
    # Get best bid (highest price someone will pay)
    if bids:
        # Filter out bids with missing or invalid prices
        try:
            valid_bids = [float(bid.get('price')) for bid in bids if bid.get('price') is not None]
            if valid_bids:
                result['best_bid'] = max(valid_bids)
        except (ValueError, TypeError):
            pass
    
    # Get best ask (lowest price someone will sell)
    if asks:
        # Filter out asks with missing or invalid prices
        try:
            valid_asks = [float(ask.get('price')) for ask in asks if ask.get('price') is not None]
            if valid_asks:
                result['best_ask'] = min(valid_asks)
        except (ValueError, TypeError):
            pass
    
    # Calculate mid price and spread
    if result['best_bid'] is not None and result['best_ask'] is not None:
        result['mid_price'] = (result['best_bid'] + result['best_ask']) / 2
        result['spread'] = result['best_ask'] - result['best_bid']
    
    return result


def collect_live_prices(client: PolymarketClient, markets: list) -> list:
    """
    Collect live prices for all markets using CLOB API.
    
    Args:
        client: PolymarketClient instance
        markets: List of market dictionaries from Script 01
        
    Returns:
        List of live price dictionaries
    """
    live_prices = []
    timestamp = datetime.now(timezone.utc).isoformat()
    
    logger.info(f"🔍 Collecting live prices for {len(markets)} markets...")
    
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
        
        price_data = {
            'market_id': market_id,
            'question': question,
            'yes_token_id': yes_token_id,
            'no_token_id': no_token_id,
            'timestamp': timestamp
        }
        
        # Fetch YES token orderbook
        yes_orderbook = client.get_orderbook(yes_token_id)
        yes_prices = parse_orderbook(yes_orderbook)
        
        price_data['yes_best_bid'] = yes_prices['best_bid']
        price_data['yes_best_ask'] = yes_prices['best_ask']
        price_data['yes_mid_price'] = yes_prices['mid_price']
        price_data['yes_spread'] = yes_prices['spread']
        
        # Fetch NO token orderbook
        no_orderbook = client.get_orderbook(no_token_id)
        no_prices = parse_orderbook(no_orderbook)
        
        price_data['no_best_bid'] = no_prices['best_bid']
        price_data['no_best_ask'] = no_prices['best_ask']
        price_data['no_mid_price'] = no_prices['mid_price']
        price_data['no_spread'] = no_prices['spread']
        
        live_prices.append(price_data)
        
        # Log summary
        if yes_prices['mid_price'] is not None:
            logger.info(f"  YES: ${yes_prices['mid_price']:.4f} (spread: ${yes_prices['spread']:.4f})")
        else:
            logger.info(f"  YES: No orderbook data")
        
        if no_prices['mid_price'] is not None:
            logger.info(f"  NO:  ${no_prices['mid_price']:.4f} (spread: ${no_prices['spread']:.4f})")
        else:
            logger.info(f"  NO:  No orderbook data")
    
    logger.info(f"✅ Collected live prices for {len(live_prices)} markets")
    
    return live_prices


def save_live_prices(prices: list):
    """
    Save live prices to JSON file.
    
    Args:
        prices: List of price dictionaries
    """
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    logger.info(f"📂 Saving live prices to {OUTPUT_FILE}...")
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(prices, f, indent=4)
        logger.info("✅ Live prices saved successfully!")
    except IOError as e:
        logger.error(f"❌ Error saving to file: {e}")
        sys.exit(1)


def main():
    """
    Main function to collect and save live prices.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Collect live prices for Polymarket markets',
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
        
        # Collect live prices
        live_prices = collect_live_prices(client, markets)
        
        if live_prices:
            # Save to file
            save_live_prices(live_prices)
            
            # Display summary
            logger.info("\n📊 Summary:")
            logger.info(f"  Markets processed: {len(markets)}")
            logger.info(f"  Prices collected: {len(live_prices)}")
            
            # Show sample
            if live_prices:
                logger.info("\n💰 Sample prices (first 3):")
                for i, price in enumerate(live_prices[:3], 1):
                    logger.info(f"{i}. {price['question'][:50]}...")
                    if price['yes_mid_price'] is not None:
                        logger.info(f"   YES mid: ${price['yes_mid_price']:.4f}")
                    else:
                        logger.info("   YES mid: N/A")
                    if price['no_mid_price'] is not None:
                        logger.info(f"   NO mid:  ${price['no_mid_price']:.4f}")
                    else:
                        logger.info("   NO mid:  N/A")
        else:
            logger.warning("❌ No live prices collected.")
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
