"""
Script 04: Database Setup
Creates DuckDB database with tables, sequences, and indexes for the Polymarket Edge Finder.
"""

import duckdb
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database file path
DB_PATH = 'data/polymarket_edge.duckdb'


def setup_database():
    """
    Create DuckDB database with all required tables, sequences, and indexes.
    """
    try:
        # Ensure data directory exists
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        
        logger.info(f"🔧 Setting up database at {DB_PATH}...")
        
        # Connect to database
        conn = duckdb.connect(DB_PATH)
        
        # Create sequences FIRST (before tables that reference them)
        logger.info("Creating sequences...")
        conn.execute('CREATE SEQUENCE IF NOT EXISTS seq_price_history START 1')
        conn.execute('CREATE SEQUENCE IF NOT EXISTS seq_edges START 1')
        logger.info("  ✅ Sequences created")
        
        # Create tables
        logger.info("Creating tables...")
        
        # 1. Markets table - stores market metadata from Script 01
        conn.execute("""
            CREATE TABLE IF NOT EXISTS markets (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_price_history'),
                market_id VARCHAR NOT NULL UNIQUE,
                question VARCHAR,
                outcomes VARCHAR,
                yes_token_id VARCHAR,
                no_token_id VARCHAR,
                ending_time TIMESTAMP,
                category VARCHAR,
                tags VARCHAR,
                state VARCHAR,
                volume DOUBLE,
                liquidity DOUBLE,
                url VARCHAR,
                data_updated_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("  ✅ markets table created")
        
        # 2. Live prices table - stores current price snapshots from Script 02
        conn.execute("""
            CREATE TABLE IF NOT EXISTS live_prices (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_price_history'),
                market_id VARCHAR NOT NULL,
                question VARCHAR,
                yes_token_id VARCHAR,
                no_token_id VARCHAR,
                yes_best_bid DOUBLE,
                yes_best_ask DOUBLE,
                yes_mid_price DOUBLE,
                yes_spread DOUBLE,
                no_best_bid DOUBLE,
                no_best_ask DOUBLE,
                no_mid_price DOUBLE,
                no_spread DOUBLE,
                timestamp TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("  ✅ live_prices table created")
        
        # 3. Price history table - stores historical timeseries from Script 03
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_price_history'),
                market_id VARCHAR NOT NULL,
                question VARCHAR,
                yes_token_id VARCHAR,
                no_token_id VARCHAR,
                side VARCHAR,
                price DOUBLE,
                timestamp TIMESTAMP,
                data_collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("  ✅ price_history table created")
        
        # 4. Outcomes table - stores resolved market outcomes for calibration analysis
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outcomes (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_price_history'),
                market_id VARCHAR NOT NULL,
                question VARCHAR,
                outcome VARCHAR,
                resolved_at TIMESTAMP,
                resolution_price DOUBLE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("  ✅ outcomes table created")
        
        # 5. Edges table - detected trading opportunities
        conn.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                id INTEGER PRIMARY KEY DEFAULT nextval('seq_edges'),
                market_id VARCHAR NOT NULL,
                edge_type VARCHAR,
                edge_percentage DOUBLE,
                recommendation VARCHAR,
                market_price DOUBLE,
                fair_price DOUBLE,
                confidence DOUBLE,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        logger.info("  ✅ edges table created")
        
        # Create indexes for query performance
        logger.info("Creating indexes...")
        conn.execute('CREATE INDEX IF NOT EXISTS idx_markets_market_id ON markets(market_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_live_prices_market_id ON live_prices(market_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_live_prices_timestamp ON live_prices(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_market_id ON price_history(market_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_outcomes_market_id ON outcomes(market_id)')
        logger.info("  ✅ Indexes created")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Database initialized successfully at {DB_PATH}")
        logger.info("Tables created:")
        logger.info("  - markets (market metadata)")
        logger.info("  - live_prices (current orderbook snapshots)")
        logger.info("  - price_history (historical timeseries)")
        logger.info("  - outcomes (resolved market outcomes)")
        logger.info("  - edges (detected trading opportunities)")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error setting up database: {e}", exc_info=True)
        return False


def main():
    """
    Main function to set up the database.
    """
    success = setup_database()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()