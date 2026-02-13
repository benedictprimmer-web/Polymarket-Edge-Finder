"""
Script 01: Market Discovery
Fetches all active markets from Polymarket's Gamma API with pagination.
Captures market metadata including token IDs needed for CLOB API calls.
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
OUTPUT_FILE = "data/markets_snapshot.json"
PAGE_SIZE = 100  # Gamma API max per request


def extract_token_ids(market: dict) -> tuple:
    """
    Extract YES and NO token IDs from a market.
    
    The token IDs can be in different fields depending on the API response:
    - clobTokenIds: Array of token IDs [yes_token_id, no_token_id]
    - tokens: Array of token objects with 'token_id' and 'outcome'
    
    Args:
        market: Market dictionary from API
        
    Returns:
        Tuple of (yes_token_id, no_token_id), both may be None if not found
    """
    yes_token_id = None
    no_token_id = None
    
    # Try clobTokenIds first (array format)
    clob_token_ids = market.get('clobTokenIds', [])
    if clob_token_ids and len(clob_token_ids) >= 2:
        yes_token_id = clob_token_ids[0]
        no_token_id = clob_token_ids[1]
        return yes_token_id, no_token_id
    
    # Try tokens array (object format with outcome field)
    tokens = market.get('tokens', [])
    for token in tokens:
        outcome = token.get('outcome', '').lower()
        token_id = token.get('token_id') or token.get('tokenId')
        
        if outcome == 'yes' and token_id:
            yes_token_id = token_id
        elif outcome == 'no' and token_id:
            no_token_id = token_id
    
    return yes_token_id, no_token_id


def fetch_all_markets(client: PolymarketClient, active_only: bool = True) -> list:
    """
    Fetch all markets from the Polymarket Gamma API with pagination.
    
    Args:
        client: PolymarketClient instance
        active_only: If True, filter only active markets (default: True)
        
    Returns:
        List of market dictionaries with captured metadata
    """
    all_markets = []
    offset = 0
    page_num = 1
    
    logger.info("🔍 Starting market discovery from Polymarket Gamma API...")
    
    while True:
        logger.info(f"Fetching page {page_num} (offset={offset}, limit={PAGE_SIZE})...")
        
        # Fetch a page of markets
        markets_page = client.get_markets(limit=PAGE_SIZE, offset=offset, closed=False if active_only else None)
        
        if not markets_page:
            logger.info("No more markets returned. Pagination complete.")
            break
        
        logger.info(f"  Retrieved {len(markets_page)} markets on page {page_num}")
        
        # Process each market and extract relevant data
        for market in markets_page:
            # Extract token IDs
            yes_token_id, no_token_id = extract_token_ids(market)
            
            # Build market data structure
            market_data = {
                'question': market.get('question'),
                'market_id': market.get('id') or market.get('conditionId'),
                'outcomes': market.get('outcomes', []),
                'yes_token_id': yes_token_id,
                'no_token_id': no_token_id,
                'ending_time': market.get('end_date_iso') or market.get('endDate') or market.get('ending_time'),
                'category': market.get('category', 'unknown'),
                'tags': market.get('tags', []),
                'state': 'closed' if market.get('closed', False) else 'active',
                'volume': market.get('volume'),
                'liquidity': market.get('liquidity'),
                'url': f"https://polymarket.com/event/{market.get('slug', market.get('id', ''))}",
                'data_updated_at': datetime.now(timezone.utc).isoformat(),
            }
            
            # Filter by state if active_only is True
            if active_only:
                # Check if market is active (not closed)
                is_closed = market.get('closed', False)
                if not is_closed:
                    all_markets.append(market_data)
            else:
                all_markets.append(market_data)
        
        # Check if we should continue pagination
        if len(markets_page) < PAGE_SIZE:
            # Received fewer markets than requested, we've reached the end
            logger.info("Received fewer markets than page size. Reached end of results.")
            break
        
        # Move to next page
        offset += PAGE_SIZE
        page_num += 1
    
    logger.info(f"✅ Market discovery complete!")
    logger.info(f"  Total markets fetched: {len(all_markets)}")
    
    return all_markets


def save_markets_to_file(markets: list):
    """
    Save market metadata to a JSON file.
    
    Args:
        markets: List of market dictionaries
    """
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    logger.info(f"📂 Saving {len(markets)} markets to {OUTPUT_FILE}...")
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(markets, f, indent=4)
        logger.info("✅ Market data saved successfully!")
    except IOError as e:
        logger.error(f"❌ Error saving to file: {e}")
        sys.exit(1)


def main():
    """
    Main function to fetch and save active markets data.
    """
    try:
        # Initialize API client
        client = PolymarketClient(rate_limit_delay=0.5)
        
        # Fetch all active markets with pagination
        markets = fetch_all_markets(client, active_only=True)
        
        if markets:
            # Save to file
            save_markets_to_file(markets)
            
            # Display sample markets
            logger.info("\n📊 Sample markets (first 5):")
            for i, market in enumerate(markets[:5], 1):
                logger.info(f"{i}. {market['question']}")
                logger.info(f"   Market ID: {market['market_id']}")
                logger.info(f"   YES Token: {market['yes_token_id']}")
                logger.info(f"   NO Token: {market['no_token_id']}")
                logger.info(f"   Ends: {market['ending_time']}")
                logger.info("")
        else:
            logger.warning("❌ No active markets found.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
