"""
Script 02: Collect Live Prices
Fetches current orderbook data for markets using the CLOB API.
Reads market data from Script 01's output and calculates bid/ask/mid/spread.
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
        # Bids are typically sorted highest first, but let's be safe
        try:
            best_bid = max(float(bid.get('price', 0)) for bid in bids)
            result['best_bid'] = best_bid
        except (ValueError, TypeError):
            pass
    
    # Get best ask (lowest price someone will sell)
    if asks:
        # Asks are typically sorted lowest first, but let's be safe
        try:
            best_ask = min(float(ask.get('price', float('inf'))) for ask in asks)
            if best_ask != float('inf'):
                result['best_ask'] = best_ask
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
    try:
        # Load markets from Script 01
        markets = load_markets()
        
        # Initialize API client
        client = PolymarketClient(rate_limit_delay=0.5)
        
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
