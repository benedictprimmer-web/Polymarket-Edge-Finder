# Polymarket Edge Finder – Implementation Strategy

## 📋 Overview

This document is your **step-by-step execution plan** for building a Polymarket edge-finding tool. 

**Goal:** Find mispriced bets on Polymarket by analyzing historical data and detecting edges.

**High-level approach:**
1. Collect historical market prices from Polymarket APIs
2. Store prices in a database (DuckDB)
3. Analyze calibration (compare prices to actual outcomes)
4. Detect current edges (opportunities where math favors you)
5. Integrate with Claude AI for conversational analysis

---

## 🎯 The Core Idea

From the article you read:
- **Longshot bias**: Cheap NO bets (longshots) are overpriced relative to reality
- **Impatient buyer tax**: Takers (market orders) pay higher fees than makers
- **Our strategy**: Find and exploit these inefficiencies using data + AI

---

## 📊 Complete Phase-by-Phase Plan

### **PHASE 0: Setup & Foundation** (1-2 hours)

**Goal:** Get your project initialized and ready to code.

#### Step 0.1: Create GitHub Repository
- [ ] Go to github.com
- [ ] Click **+** → **New repository**
- [ ] Name: `polymarket-edge-finder`
- [ ] Set to Public
- [ ] Click Create

**Deliverable:** `https://github.com/benedictprimmer-web/polymarket-edge-finder`

---

#### Step 0.2: Create Initial Files

Create these files in your repo (using GitHub's "Add file" button):

**File 1: `README.md`**
```
# Polymarket Edge Finder

A data-driven tool to identify mispriced bets on Polymarket.

## Status
🚧 In Development

## Quick Start
```bash
pip install -r requirements.txt
python scripts/01_discover_markets.py
```

## Implementation Plan
See `STRATEGY.md` for the complete step-by-step guide.
```

**File 2: `requirements.txt`**
```
requests==2.31.0
httpx==0.25.0
pandas==2.1.0
duckdb==0.9.0
pyarrow==13.0.0
python-dotenv==1.0.0
click==8.1.0
jupyter==1.0.0
```

**File 3: `.gitignore`**
```
__pycache__/
*.pyc
.env
.DS_Store
*.duckdb
data/
*.json
.ipynb_checkpoints/
```

**Deliverable:** All three files in your repo root

---

#### Step 0.3: Create Folder Structure

Create empty folders by adding placeholder files:

- Create `scripts/.gitkeep`
- Create `mcp/.gitkeep`
- Create `data/.gitkeep`
- Create `notebooks/.gitkeep`

**Deliverable:** Folder structure ready for scripts

---

### **PHASE 1: Data Collection** (3-4 hours)

**Goal:** Fetch data from Polymarket APIs.

#### Step 1.1: Market Discovery Script

**File:** `scripts/01_discover_markets.py`

**What it does:**
- Connects to Polymarket Gamma API
- Lists all open markets
- Saves market metadata (question, token IDs, etc.) to JSON

**How to use:**
```bash
python scripts/01_discover_markets.py
```

**Output:** `data/markets_snapshot.json` (list of all markets)

**Key info to capture:**
- Market ID
- Market question
- Category (sports, politics, crypto, etc.)
- YES token ID
- NO token ID

---

#### Step 1.2: Live Prices Script

**File:** `scripts/02_collect_live_prices.py`

**What it does:**
- Fetches current orderbook for each market
- Gets best bid/ask prices (the "live" prices RIGHT NOW)
- Calculates mid-price and spread
- Saves to JSON

**How to use:**
```bash
python scripts/02_collect_live_prices.py
```

**Output:** `data/live_prices.json` (snapshot of current prices)

**Key info to capture:**
- Best bid price (highest someone will pay for YES)
- Best ask price (lowest someone will sell YES for)
- Mid-price (average of bid and ask)
- Spread (difference between bid and ask)
- Timestamp of snapshot

---

#### Step 1.3: Historical Prices Script

**File:** `scripts/03_collect_historical_prices.py`

**What it does:**
- Fetches 30-day historical price data from CLOB API
- Gets hourly price snapshots for past month
- Saves all historical data to JSON

**How to use:**
```bash
python scripts/03_collect_historical_prices.py
```

**Output:** `data/historical_prices.json` (30 days of price history)

**Key info to capture:**
- For each market:
  - YES price at each hour (past 30 days)
  - NO price at each hour (past 30 days)
  - Timestamp for each price point

---

### **PHASE 2: Data Storage** (1-2 hours)

**Goal:** Store collected data in a database for analysis.

We're using **DuckDB** (like the article's author did with Kalshi data).

#### Step 2.1: Database Setup Script

**File:** `scripts/04_setup_database.py`

**What it does:**
- Creates DuckDB database file
- Defines table schemas (structure for storing data)
- Initializes empty database

**How to use:**
```bash
python scripts/04_setup_database.py
```

**Output:** `data/polymarket.duckdb` (empty database, ready for data)

**Tables created:**
```
1. markets
   - market_id (unique identifier)
   - question (the market question)
   - category (sports, politics, etc.)
   - yes_token_id (token ID for YES side)
   - no_token_id (token ID for NO side)

2. price_history
   - token_id (which token)
   - market_id (which market)
   - timestamp (when this price was)
   - price (the price value)
   - side (YES or NO)

3. live_prices
   - market_id
   - yes_price (current YES price)
   - no_price (current NO price)
   - yes_spread (bid-ask spread for YES)
   - no_spread (bid-ask spread for NO)
   - snapshot_time (when taken)

4. edges
   - market_id
   - edge_type (LONGSHOT_BIAS, etc.)
   - edge_percentage (how strong the edge is)
   - recommendation (BUY_YES or BUY_NO)
   - market_price (current price)
   - fair_price (what we think it should be)
```

---

#### Step 2.2: Data Ingestion Script

**File:** `scripts/05_ingest_data.py`

**What it does:**
- Reads JSON files from Phase 1
- Converts them to structured data
- Inserts into DuckDB database

**How to use:**
```bash
python scripts/05_ingest_data.py
```

**Process:**
1. Read `markets_snapshot.json` → Insert into `markets` table
2. Read `historical_prices.json` → Insert into `price_history` table
3. Read `live_prices.json` → Insert into `live_prices` table

**Output:** Populated DuckDB database

---

### **PHASE 3: Analysis & Edge Detection** (2-3 hours)

**Goal:** Analyze the data and find edges.

#### Step 3.1: Calibration Analysis Script

**File:** `scripts/06_calibration_analysis.py`

**What it does:**
- Groups historical prices into buckets (e.g., 0-10¢, 10-20¢, etc.)
- For each bucket, calculates statistics:
  - Average price
  - How often that price level actually resolved YES/NO
  - Implied probability vs actual outcome

**How to use:**
```bash
python scripts/06_calibration_analysis.py
```

**Output:** Printed analysis (and optional JSON file)

**Example output:**
```
NO prices in 01-10¢ bucket:
  - 1,234 historical prices
  - Average: 0.08 (8¢)
  - Resolved YES: 1.2% of the time
  - Implied probability: 8%
  - Edge: +6.8% (YES underpriced)
```

**Key insight:** If NO at 8¢ historically wins <8% of the time, then NO is underpriced (good bet)

---

#### Step 3.2: Edge Detection Script

**File:** `scripts/07_detect_edges.py`

**What it does:**
- Looks at current live prices
- Compares to historical calibration data
- Flags markets where math says there's an edge
- Ranks by edge strength

**How to use:**
```bash
python scripts/07_detect_edges.py
```

**Output:** `data/detected_edges.json` (list of opportunities)

**Example edge detection:**
```
Market: "Will Trump win the 2024 election?"
Current NO price: 0.12 (12¢)

Historical data: NO at 12¢ has won 6% of the time
But implied probability: 12%

Edge: +6% on NO (if math holds)
Recommendation: BUY_NO

Reasoning: Cheap longshot (12¢) appears overpriced based on history
```

---

### **PHASE 4: MCP Integration** (2-3 hours)

**Goal:** Connect your analysis to Claude AI.

#### Step 4.1: MCP Server

**File:** `mcp/mcp_server.py`

**What it does:**
- Creates a "tool server" that Claude can talk to
- Exposes your analysis functions as callable tools
- Claude can ask: "What's the edge on market XYZ?" and get instant answers

**How to use:**
```bash
python mcp/mcp_server.py
```

**Tools exposed to Claude:**

1. **`get_calibration`**
   - Input: Price bucket (e.g., "01-10¢"), Side (YES/NO)
   - Output: Historical data for that bucket
   - Claude use: "Show me how 10¢ NO bets have historically performed"

2. **`get_edges`**
   - Input: None
   - Output: List of detected edges
   - Claude use: "What edges do we have right now?"

3. **`analyze_market`**
   - Input: Market ID
   - Output: Deep dive into that market's data
   - Claude use: "Analyze market ABC123 for me"

---

### **PHASE 5: Testing & Validation** (1-2 hours)

**Goal:** Verify everything works end-to-end.

#### Step 5.1: End-to-End Test Script

**File:** `scripts/08_end_to_end_test.py`

**What it does:**
- Runs all scripts in order
- Checks that each produces expected output
- Reports which steps passed/failed

**How to use:**
```bash
python scripts/08_end_to_end_test.py
```

**Expected output:**
```
✅ Phase 1.1: Market Discovery - PASS
✅ Phase 1.2: Live Prices - PASS
✅ Phase 1.3: Historical Prices - PASS
✅ Phase 2.1: Database Setup - PASS
✅ Phase 2.2: Data Ingestion - PASS
✅ Phase 3.1: Calibration Analysis - PASS
✅ Phase 3.2: Edge Detection - PASS

Result: 7/7 steps passed ✅
```

---

### **PHASE 6: Iteration & Improvement** (Ongoing)

**Goal:** Refine your strategy based on results.

#### What to do:
1. Review detected edges
2. Check if recommendations would have made money historically
3. Adjust detection logic if needed
4. Automate data collection (run daily/hourly)
5. Build dashboard to visualize edges
6. Integrate with Polymarket to actually place bets (optional, advanced)

---

## 🏃 Quick Execution Order

Run these steps in order:

```bash
# Phase 0: Already done (files created)

# Phase 1: Collect data
python scripts/01_discover_markets.py
python scripts/02_collect_live_prices.py
python scripts/03_collect_historical_prices.py

# Phase 2: Store data
python scripts/04_setup_database.py
python scripts/05_ingest_data.py

# Phase 3: Analyze & detect edges
python scripts/06_calibration_analysis.py
python scripts/07_detect_edges.py

# Phase 5: Test everything
python scripts/08_end_to_end_test.py

# Phase 4: (Optional) Start MCP server for Claude
python mcp/mcp_server.py
```

---

## 📈 Success Metrics

Track these as you build:

- [ ] # of markets discovered: ______
- [ ] # of price points collected: ______
- [ ] Database size (MB): ______
- [ ] # of potential edges detected: ______
- [ ] Strongest edge found (%): ______
- [ ] Markets analyzed: ______

---

## 🐛 Troubleshooting

**"API returned error"**
- Check your internet connection
- Verify API endpoints are still working
- Add delays between requests (don't spam API)

**"File not found"**
- Make sure you ran previous scripts first
- Check file paths match what's expected

**"Database error"**
- Make sure you ran database setup first (`scripts/04_setup_database.py`)
- Check DuckDB is installed: `pip install duckdb`

**"Not enough data"**
- Run historical prices collection multiple times to build up data
- May need 2-3 runs to get meaningful statistics

---

## 🚀 Next Steps After Phase 1-3

Once you complete Phase 1-3 (data collection, storage, analysis):

1. **Examine the edges you found**
   - Do they make sense?
   - Are they strong enough to trade on?

2. **Backtest your strategy**
   - Would these edges have made money in the past?

3. **Automate collection**
   - Set up a cron job or GitHub Action to run daily
   - Build historical data over time

4. **Connect to Claude** (Phase 4)
   - Ask conversational questions about your data
   - Let AI help find patterns

5. **Optional: Actually trade**
   - Use Polymarket's trading API to place bets
   - Start small while testing

---

## 📚 Key Files Reference

| File | Purpose | Input | Output |
|------|---------|-------|--------|
| `01_discover_markets.py` | Find all markets | Polymarket API | `markets_snapshot.json` |
| `02_collect_live_prices.py` | Current prices | Polymarket API | `live_prices.json` |
| `03_collect_historical_prices.py` | Historical prices | Polymarket API | `historical_prices.json` |
| `04_setup_database.py` | Create database | None | `polymarket.duckdb` |
| `05_ingest_data.py` | Load JSON to DB | JSON files | DuckDB tables |
| `06_calibration_analysis.py` | Analyze calibration | DuckDB | Console output |
| `07_detect_edges.py` | Find edges | DuckDB | `detected_edges.json` |
| `08_end_to_end_test.py` | Test everything | All scripts | Pass/fail report |

---

## ✅ Checklist

Track your progress:

- [ ] Phase 0.1: Create GitHub repo
- [ ] Phase 0.2: Add README, requirements, .gitignore
- [ ] Phase 0.3: Create folder structure
- [ ] Phase 1.1: Write & test market discovery script
- [ ] Phase 1.2: Write & test live prices script
- [ ] Phase 1.3: Write & test historical prices script
- [ ] Phase 2.1: Write & test database setup script
- [ ] Phase 2.2: Write & test data ingestion script
- [ ] Phase 3.1: Write & test calibration analysis script
- [ ] Phase 3.2: Write & test edge detection script
- [ ] Phase 5.1: Write & run end-to-end test
- [ ] Review detected edges
- [ ] Phase 4.1: (Optional) Build MCP server
- [ ] Phase 6: Iterate and improve

---

## 💡 Tips

- **Start small:** Run Phase 1-2 first to verify APIs work
- **Test incrementally:** After each script, check the output file
- **Save your data:** Once you have 30+ days of prices, back them up
- **Document what you learn:** Keep a log of interesting patterns found
- **Iterate:** Your edge detection will improve with more data and refinement

---

## 📖 Resources

- [Polymarket CLOB API Docs](https://docs.polymarket.com/api)
- [Polymarket Gamma API](https://gamma-api.polymarket.com)
- [DuckDB Documentation](https://duckdb.org/docs)
- [Original article referenced](Link to the article you read)

---

**Last updated:** Today  
**Status:** Ready to start Phase 0-1
