"""
Script 05: Data Ingestion
Reads JSON output files from Scripts 01-03 and inserts data into DuckDB.
"""

import duckdb
import json
import os
import sys
import logging
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# File paths
DB_PATH = 'data/polymarket_edge.duckdb'
MARKETS_FILE = 'data/markets_snapshot.json'
LIVE_PRICES_FILE = 'data/live_prices.json'
HISTORICAL_PRICES_FILE = 'data/historical_prices.json'


def load_json_file(filepath):
    """
    Load and parse a JSON file.
    
    Args:
        filepath: Path to the JSON file
        
    Returns:
        Parsed JSON data or None if file doesn't exist
    """
    if not os.path.exists(filepath):
        logger.warning(f"File not found: {filepath}")
        return None
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        logger.info(f"✅ Loaded {filepath}")
        return data
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error parsing JSON from {filepath}: {e}")
        return None
    except IOError as e:
        logger.error(f"❌ Error reading file {filepath}: {e}")
        return None


def ingest_markets(conn, markets_data):
    """
    Ingest market metadata into the markets table.
    Uses upsert logic: update if exists, insert if new.
    
    Args:
        conn: DuckDB connection
        markets_data: List of market dictionaries
        
    Returns:
        Tuple of (inserted_count, updated_count)
    """
    if not markets_data:
        logger.warning("No markets data to ingest")
        return 0, 0
    
    logger.info(f"📥 Ingesting {len(markets_data)} markets...")
    
    inserted_count = 0
    updated_count = 0
    
    for market in markets_data:
        market_id = market.get('market_id')
        if not market_id:
            logger.warning("Skipping market without market_id")
            continue
        
        # Check if market already exists
        existing = conn.execute(
            "SELECT market_id FROM markets WHERE market_id = ?", 
            [market_id]
        ).fetchone()
        
        # Convert lists to JSON strings for storage
        outcomes_json = json.dumps(market.get('outcomes', []))
        tags_json = json.dumps(market.get('tags', []))
        
        if existing:
            # Update existing market
            conn.execute("""
                UPDATE markets 
                SET question = ?,
                    outcomes = ?,
                    yes_token_id = ?,
                    no_token_id = ?,
                    ending_time = ?,
                    category = ?,
                    tags = ?,
                    state = ?,
                    volume = ?,
                    liquidity = ?,
                    url = ?,
                    data_updated_at = ?
                WHERE market_id = ?
            """, [
                market.get('question'),
                outcomes_json,
                market.get('yes_token_id'),
                market.get('no_token_id'),
                market.get('ending_time'),
                market.get('category'),
                tags_json,
                market.get('state'),
                market.get('volume'),
                market.get('liquidity'),
                market.get('url'),
                market.get('data_updated_at'),
                market_id
            ])
            updated_count += 1
        else:
            # Insert new market
            conn.execute("""
                INSERT INTO markets (
                    market_id, question, outcomes, yes_token_id, no_token_id,
                    ending_time, category, tags, state, volume, liquidity,
                    url, data_updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                market_id,
                market.get('question'),
                outcomes_json,
                market.get('yes_token_id'),
                market.get('no_token_id'),
                market.get('ending_time'),
                market.get('category'),
                tags_json,
                market.get('state'),
                market.get('volume'),
                market.get('liquidity'),
                market.get('url'),
                market.get('data_updated_at')
            ])
            inserted_count += 1
    
    conn.commit()
    logger.info(f"  ✅ Markets: {inserted_count} inserted, {updated_count} updated")
    return inserted_count, updated_count


def ingest_live_prices(conn, live_prices_data):
    """
    Ingest live price snapshots into the live_prices table.
    Each run appends new snapshots (no deletion).
    Deduplicates based on market_id + timestamp.
    
    Args:
        conn: DuckDB connection
        live_prices_data: List of price snapshot dictionaries
        
    Returns:
        Number of snapshots inserted
    """
    if not live_prices_data:
        logger.warning("No live prices data to ingest")
        return 0
    
    logger.info(f"📥 Ingesting {len(live_prices_data)} live price snapshots...")
    
    inserted_count = 0
    skipped_count = 0
    
    for price in live_prices_data:
        market_id = price.get('market_id')
        timestamp = price.get('timestamp')
        
        if not market_id or not timestamp:
            logger.warning("Skipping price snapshot without market_id or timestamp")
            continue
        
        # Check if this exact snapshot already exists (deduplication)
        existing = conn.execute("""
            SELECT id FROM live_prices 
            WHERE market_id = ? AND timestamp = ?
        """, [market_id, timestamp]).fetchone()
        
        if existing:
            skipped_count += 1
            continue
        
        # Insert new price snapshot
        conn.execute("""
            INSERT INTO live_prices (
                market_id, question, yes_token_id, no_token_id,
                yes_best_bid, yes_best_ask, yes_mid_price, yes_spread,
                no_best_bid, no_best_ask, no_mid_price, no_spread,
                timestamp
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            market_id,
            price.get('question'),
            price.get('yes_token_id'),
            price.get('no_token_id'),
            price.get('yes_best_bid'),
            price.get('yes_best_ask'),
            price.get('yes_mid_price'),
            price.get('yes_spread'),
            price.get('no_best_bid'),
            price.get('no_best_ask'),
            price.get('no_mid_price'),
            price.get('no_spread'),
            timestamp
        ])
        inserted_count += 1
    
    conn.commit()
    logger.info(f"  ✅ Live prices: {inserted_count} inserted, {skipped_count} skipped (duplicates)")
    return inserted_count


def ingest_historical_prices(conn, historical_data):
    """
    Ingest historical price timeseries into the price_history table.
    Flattens the nested structure: each historical data point becomes a row.
    Deduplicates based on market_id + side + timestamp.
    
    Args:
        conn: DuckDB connection
        historical_data: Dictionary with market_id as keys
        
    Returns:
        Number of historical data points inserted
    """
    if not historical_data:
        logger.warning("No historical prices data to ingest")
        return 0
    
    logger.info(f"📥 Ingesting historical prices for {len(historical_data)} markets...")
    
    inserted_count = 0
    skipped_count = 0
    
    for market_id, market_history in historical_data.items():
        if not market_history:
            continue
        
        question = market_history.get('question')
        yes_token_id = market_history.get('yes_token_id')
        no_token_id = market_history.get('no_token_id')
        
        # Process YES history
        yes_history = market_history.get('yes_history')
        if yes_history and isinstance(yes_history, dict):
            history_points = yes_history.get('history', [])
            if isinstance(history_points, list):
                for point in history_points:
                    timestamp_unix = point.get('t')
                    price = point.get('p')
                    
                    if timestamp_unix is None or price is None:
                        continue
                    
                    # Convert Unix timestamp to ISO format
                    timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc).isoformat()
                    
                    # Check if this data point already exists (deduplication)
                    existing = conn.execute("""
                        SELECT id FROM price_history 
                        WHERE market_id = ? AND side = ? AND timestamp = ?
                    """, [market_id, 'YES', timestamp]).fetchone()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Insert new historical data point
                    conn.execute("""
                        INSERT INTO price_history (
                            market_id, question, yes_token_id, no_token_id,
                            side, price, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, [
                        market_id, question, yes_token_id, no_token_id,
                        'YES', price, timestamp
                    ])
                    inserted_count += 1
        
        # Process NO history
        no_history = market_history.get('no_history')
        if no_history and isinstance(no_history, dict):
            history_points = no_history.get('history', [])
            if isinstance(history_points, list):
                for point in history_points:
                    timestamp_unix = point.get('t')
                    price = point.get('p')
                    
                    if timestamp_unix is None or price is None:
                        continue
                    
                    # Convert Unix timestamp to ISO format
                    timestamp = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc).isoformat()
                    
                    # Check if this data point already exists (deduplication)
                    existing = conn.execute("""
                        SELECT id FROM price_history 
                        WHERE market_id = ? AND side = ? AND timestamp = ?
                    """, [market_id, 'NO', timestamp]).fetchone()
                    
                    if existing:
                        skipped_count += 1
                        continue
                    
                    # Insert new historical data point
                    conn.execute("""
                        INSERT INTO price_history (
                            market_id, question, yes_token_id, no_token_id,
                            side, price, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, [
                        market_id, question, yes_token_id, no_token_id,
                        'NO', price, timestamp
                    ])
                    inserted_count += 1
    
    conn.commit()
    logger.info(f"  ✅ Price history: {inserted_count} inserted, {skipped_count} skipped (duplicates)")
    return inserted_count


def main():
    """
    Main function to ingest all data into the database.
    """
    logger.info("🚀 Starting data ingestion...")
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        logger.error(f"❌ Database not found at {DB_PATH}")
        logger.error("Please run scripts/04_setup_database.py first")
        sys.exit(1)
    
    try:
        # Connect to database
        conn = duckdb.connect(DB_PATH)
        logger.info(f"✅ Connected to database at {DB_PATH}")
        
        # Load JSON files
        markets_data = load_json_file(MARKETS_FILE)
        live_prices_data = load_json_file(LIVE_PRICES_FILE)
        historical_data = load_json_file(HISTORICAL_PRICES_FILE)
        
        # Track summary stats
        summary = {
            'markets_inserted': 0,
            'markets_updated': 0,
            'live_prices_inserted': 0,
            'history_points_inserted': 0
        }
        
        # Ingest markets
        if markets_data:
            inserted, updated = ingest_markets(conn, markets_data)
            summary['markets_inserted'] = inserted
            summary['markets_updated'] = updated
        
        # Ingest live prices
        if live_prices_data:
            inserted = ingest_live_prices(conn, live_prices_data)
            summary['live_prices_inserted'] = inserted
        
        # Ingest historical prices
        if historical_data:
            inserted = ingest_historical_prices(conn, historical_data)
            summary['history_points_inserted'] = inserted
        
        # Close connection
        conn.close()
        
        # Display summary
        logger.info("\n" + "="*60)
        logger.info("📊 INGESTION SUMMARY")
        logger.info("="*60)
        logger.info(f"Markets inserted:          {summary['markets_inserted']}")
        logger.info(f"Markets updated:           {summary['markets_updated']}")
        logger.info(f"Live price snapshots:      {summary['live_prices_inserted']}")
        logger.info(f"Historical data points:    {summary['history_points_inserted']}")
        logger.info("="*60)
        logger.info("✅ Data ingestion completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Fatal error during ingestion: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
