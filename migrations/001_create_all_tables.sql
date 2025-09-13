-- Create stock_price_history table for storing daily stock data
CREATE TABLE IF NOT EXISTS stock_price_history (
    id VARCHAR(36) PRIMARY KEY,
    company_symbol VARCHAR(30) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    last_traded_price DECIMAL(18, 8) NOT NULL,
    market_cap DECIMAL(20, 2) NOT NULL,
    one_day_return DECIMAL(10, 4),
    created_at DATE NOT NULL,
    UNIQUE (company_symbol, created_at)
);

-- Create index_compositions table for storing daily index composition
CREATE TABLE IF NOT EXISTS index_compositions (
    id VARCHAR(36) PRIMARY KEY,
    date DATE NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    weight_percent DECIMAL(5, 3) NOT NULL,
    market_cap DECIMAL(20, 2) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    return_percent DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index_performance table for storing daily index performance metrics
CREATE TABLE IF NOT EXISTS index_performance (
    id VARCHAR(36) PRIMARY KEY,
    date DATE NOT NULL,
    daily_return_percent DECIMAL(10, 4) NOT NULL,
    cumulative_return_percent DECIMAL(10, 4) NOT NULL,
    index_value DECIMAL(18, 8) NOT NULL,
    companies_count INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_price_history(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_price_history(company_symbol);
CREATE INDEX IF NOT EXISTS idx_market_cap ON stock_price_history(market_cap);

CREATE INDEX IF NOT EXISTS idx_compositions_date ON index_compositions(date);
CREATE INDEX IF NOT EXISTS idx_compositions_symbol ON index_compositions(symbol);

CREATE INDEX IF NOT EXISTS idx_performance_date ON index_performance(date);
