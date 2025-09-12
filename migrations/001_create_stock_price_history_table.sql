-- Migration: Create stock_price_history table
-- Description: Initial schema for storing daily stock price and market cap data
-- Date: 2025-09-12

CREATE TABLE IF NOT EXISTS stock_price_history (
    id INTEGER,
    company_symbol VARCHAR(30) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    last_traded_price DECIMAL(18, 8) NOT NULL,
    market_cap DECIMAL(20, 2) NOT NULL,
    one_day_return DECIMAL(10, 4),
    created_at DATE NOT NULL,
    PRIMARY KEY (company_symbol, created_at)
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_stock_date ON stock_price_history(created_at);
CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_price_history(company_symbol);
CREATE INDEX IF NOT EXISTS idx_market_cap ON stock_price_history(market_cap);
