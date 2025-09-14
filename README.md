# Hedgineer Equal Weight Stock Index

A FastAPI application that tracks and manages a custom equal-weighted stock index comprising the top 500 US stocks by daily market capitalization, as per assignment requirements.

## Overview

This system implements an equal-weight index that:
- Fetches top 500 companies by market cap daily
- Assigns equal 0.2% weight to each company
- Provides REST APIs for index construction and analysis
- Uses multiple data sources with fallback strategy
- Runs automated daily data ingestion

## Architecture

### Clean Layered Architecture with Dependency Injection

```
┌──────────────────────────────────────────────────────────────────┐
│                       Controllers                                │
│  ┌─────────────────┐     Direct Injection     ┌─────────────────┐ │
│  │ IndexController │◄──────────────────────────│BuildIndexManager│ │
│  │                 │                           │ (Build Logic)   │ │
│  │                 │◄──────────────────────────┤ IndexManager    │ │
│  │                 │                           │ (Query + Cache) │ │
│  └─────────────────┘                           └─────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
           │                                             │
           │                    ┌─────────────────────────┼─────────┐
           │                    │                         │         │
           ▼                    ▼                         ▼         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐   │
│  Redis Service  │    │  Index Service  │    │ Repository      │   │
│  (Caching)      │    │ (Business Logic)│    │ (Data Access)   │   │
└─────────────────┘    └─────────────────┘    └─────────────────┘   │
                                                         │           │
                              ┌──────────────────────────┼───────────┘
                              │                          │
                              ▼                          ▼
                    ┌─────────────────┐       ┌─────────────────┐
                    │     DuckDB      │       │ External APIs   │
                    │   (Database)    │       │ Yahoo Finance   │
                    │   + Migrations  │       │ Alpha Vantage   │
                    └─────────────────┘       └─────────────────┘
```

### Key Architecture Benefits

- **Clean Separation**: Build operations vs Query operations with caching
- **Direct Dependencies**: Controllers inject exactly what they need  
- **Single Responsibility**: Each manager has one focused purpose
- **Dependency Injection**: All dependencies managed centrally in `container.py`
- **Loose Coupling**: Easy to test and modify individual components

## Data Sources Strategy

### Multi-Source Implementation

**Primary Source: Yahoo Finance**
- Free access, no API key required
- Good for bulk market data collection
- Fast response times for large datasets
- Limitations: Rate limiting, occasional SSL issues

**Secondary Source: Alpha Vantage**
- More detailed fundamental data
- Reliable API structure
- Limitations: API key required, stricter rate limits

**Fallback Strategy:**
1. Try Yahoo Finance for market data
2. Fall back to Alpha Vantage if Yahoo fails
3. Both sources evaluated for at least 30 days of data

## Setup & Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)

### Quick Start
```bash
# 1. Clone repository
git clone <repository-url>
cd hedgineer-equal-weight-stock

# 2. Start with Docker Compose (migrations run automatically)
docker-compose up -d

# 3. Wait for startup (migrations + automatic backfill will run)
sleep 10

# 4. Access API documentation
open http://localhost:8000/docs
```

**Note**: Database migrations run automatically on startup. The system will create the required tables and indexes on first run.

### Environment Variables
```bash
ALPHA_VANTAGE_API_KEY=your_key    # Optional: For Alpha Vantage data
DUCKDB_PATH=data/hedgineer.db     # Database file location
```

## API Endpoints

All endpoints follow assignment specifications and return JSON responses.

### 1. Index Construction

#### `POST /build-index`
**Purpose**: Build index for specified date range and persist to database

**Features:**
- Calculates compositions and performance separately  
- Persists data to database for fast retrieval
- Clean separation of build logic from query logic

**Request Body:**
```json
{
  "start_date": "2025-09-10",
  "end_date": "2025-09-12"
}
```

**Response:**
```json
{
  "success": true,
  "start_date": "2025-09-10",
  "end_date": "2025-09-12",
  "trading_days": 3,
  "total_compositions_built": 3,
  "error_message": null
}
```

### 2. Index Retrieval APIs

#### `GET /index-performance?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
**Purpose**: Return daily returns and cumulative returns (cached with Redis)

**Response:**
```json
[
  {
    "date": "2025-09-10",
    "daily_return_percent": 0.2495,
    "cumulative_return_percent": 0.2495,
    "index_value": 1002.495,
    "companies_count": 100
  },
  {
    "date": "2025-09-11",
    "daily_return_percent": -0.2784,
    "cumulative_return_percent": -0.0290,
    "index_value": 999.710,
    "companies_count": 100
  }
]
```

#### `GET /index-composition?date=YYYY-MM-DD`
**Purpose**: Return 100-stock composition for a given date (cached with Redis)

**Response:**
```json
[
  {
    "date": "2025-09-11",
    "symbol": "AAPL",
    "company_name": "Apple Inc.",
    "weight_percent": 1.0,
    "market_cap": 2580000000000.0,
    "price": 173.32,
    "return_percent": -1.52
  },
  {
    "date": "2025-09-11",
    "symbol": "MSFT",
    "company_name": "Microsoft Corporation",
    "weight_percent": 1.0,
    "market_cap": 2450000000000.0,
    "price": 329.15,
    "return_percent": 0.87
  }
]
```

#### `GET /composition-changes?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`
**Purpose**: List days when composition changed, with stocks entered/exited (cached with Redis)

**Response:**
```json
[
  {
    "date": "2025-09-11",
    "symbol": "NVDA",
    "company_name": "NVIDIA Corporation",
    "change_type": "entered",
    "previous_weight_percent": 0.0,
    "new_weight_percent": 1.0
  },
  {
    "date": "2025-09-11", 
    "symbol": "TSLA",
    "company_name": "Tesla Inc",
    "change_type": "exited",
    "previous_weight_percent": 1.0,
    "new_weight_percent": 0.0
  }
]
```

### 3. Data Export API

#### `POST /export-data`
**Purpose**: Export index data to Excel format

**Request Body:**
```json
{
  "start_date": "2025-09-10",
  "end_date": "2025-09-12"
}
```

**Response**: Excel (.xlsx) file download with sheets:
- Index Performance (daily returns, cumulative returns, index values)
- Daily Compositions (latest date composition)
- Composition Changes (stocks entered/exited)

## How Equal-Weight Index Works

### Daily Process
1. **Market Data Collection**: Fetch current market cap for 500+ companies
2. **Dynamic Ranking**: Sort all companies by market capitalization 
3. **Top 100 Selection**: Take exactly top 100 companies by market cap
4. **Equal Weight Assignment**: Assign exactly 1% weight to each company
5. **Performance Calculation**: Calculate daily returns using equal weights

### Index Calculation Formula
```python
# Equal-weight daily return = average of all stock returns
daily_return = sum(stock.one_day_return for stock in top_100) / 100

# Index value compounds daily (starts at 1000)
index_value *= (1 + daily_return / 100)

# Cumulative return from start
cumulative_return = ((index_value - 1000.0) / 1000.0) * 100
```

### Why Equal-Weight?
- **No concentration risk**: No single company dominates
- **Balanced exposure**: Every company has equal influence
- **True diversification**: Equal voice for all top 100 companies

## Automated Data Pipeline

### Cron Scheduler
- **Trigger**: Daily at midnight (00:05 AM)
- **Weekend handling**: Skips market-closed days
- **Backfill logic**: Automatically fills missing data
- **Initial setup**: Loads last 30 days on first run

### Data Storage
- **Database**: DuckDB for analytical queries
- **Schema**: Optimized for time-series financial data
- **Indexing**: Fast queries on date and market cap
- **Persistence**: Docker volume for data retention

## Key Features

### Performance Optimizations
- **Redis Caching**: All GET endpoints cache results for fast retrieval
- **Single query optimization**: Fetch date ranges in one database call instead of multiple queries
- **Window functions**: Efficient top-N selection using SQL ROW_NUMBER()
- **Clean architecture**: Separated concerns with dependency injection
- **Direct manager calls**: No unnecessary delegation layers

### Caching Strategy
- **Cache Layer**: Redis for all query endpoints with TTL
- **Build-then-Cache**: Build index persists to database, queries use cached results
- **Cache Keys**: Structured keys with date parameters for precise cache control
- **Cache Invalidation**: Automatic TTL-based expiration (1 hour default)

### Production Ready
- **Docker containerization**: Complete multi-service setup
- **Error handling**: Graceful fallbacks and error recovery
- **Logging**: Structured logging for monitoring
- **Type safety**: Full Pydantic models and type hints

## Configuration

### Key Constants
```python
# src/constants.py - Centralized configuration
TOP_COMPANIES_COUNT = 100           # Number of companies in index
DEFAULT_BACKFILL_DAYS = 30         # Historical data range  
INDEX_BASE_VALUE = 1000.0          # Starting index value
WEEKDAY_TRADING_LIMIT = 5          # Trading days (Mon-Fri)
DAILY_CRON_HOUR = 0                # Daily execution time
DAILY_CRON_MINUTE = 5              # 00:05 AM
MAX_COMPANY_SYMBOL_LENGTH = 30     # Database constraints
MAX_COMPANY_NAME_LENGTH = 100      # Database constraints  
PRICE_DECIMAL_PLACES = 8           # Precision settings
MARKET_CAP_DECIMAL_PLACES = 2      # Precision settings
```

## Development

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python main.py

# Run tests
pytest tests/
```

### Docker Setup

⚠️ **Important Startup Process**: The server automatically builds the index for the last 30 days with 500 companies on startup. **Please wait 2-3 minutes** before using the API endpoints.

```bash
# Start the application
docker-compose up -d

# View startup logs (recommended to monitor progress)
docker-compose logs -f app

# Expected startup sequence:
# 🚀 Starting initial data backfill and index building...
# ⏱️  Optimized process: ~2-3 minutes for 500 companies over 30 days
# 📊 Step 1/2: Fetching stock data for 500 companies...
# ✅ Data dumping completed! Stock data is now available.
# 📈 Step 2/2: Building index compositions and performance...
# ✅ Index building completed: X compositions built for Y trading days
# 🎉 Initial setup completed! All API endpoints are now ready for use.

# ✅ Once you see the final message, the API is ready!

# Run tests
docker run --rm -v $(pwd):/app -w /app --env DUCKDB_PATH=data/test_hedgineer.db hedgineer-equal-weight-stock-app python -m pytest tests/ -v
```

**Startup Process:**
1. **Database Migration** (< 1 second) - Creates tables if needed
2. **Stock Data Fetching** (1-2 minutes) - Downloads 30 days of data for 500 companies
   - ✅ **"Data dumping completed!"** message indicates this step is done
3. **Index Building** (30-60 seconds) - Calculates compositions and performance metrics
4. **API Ready** - 🎉 **"All API endpoints are now ready for use"** message confirms completion

### Database Schema & Migrations

The application uses a migration system for database schema management. Migrations run automatically on startup.

**Migration Files:**
- `001_create_stock_price_history_table.sql` - Core stock data table
- `002_create_index_tables.sql` - Index compositions and performance tables

#### Data Models

**StockPriceHistory** - Raw market data storage
- `company_symbol` - Stock ticker (max 30 chars)
- `company_name` - Company full name (max 100 chars) 
- `last_traded_price` - Current stock price (8 decimal precision)
- `market_cap` - Market capitalization (2 decimal precision)
- `one_day_return` - Daily return percentage
- `created_at` - Trading date

**IndexComposition** - Equal-weight index components
- `date` - Composition date
- `symbol` - Stock ticker
- `company_name` - Company name
- `weight_percent` - Always 1.0% (equal weight)
- `market_cap` - Market capitalization at composition
- `price` - Stock price at composition
- `return_percent` - Daily return for this stock

**IndexPerformance** - Index performance metrics
- `date` - Performance date
- `daily_return_percent` - Index daily return
- `cumulative_return_percent` - Total return from base
- `index_value` - Current index value (starts at 1000.0)
- `companies_count` - Number of companies in index (100)

**Database Setup:** Check `migrations/` folder for complete schema setup scripts.

#### Running Migrations Manually
```bash
# Run database setup script
python setup_database.py

# Or run migrations directly
python migrations/migration_runner.py
```

Built for production-grade financial data analysis with focus on equal-weight indexing principles.