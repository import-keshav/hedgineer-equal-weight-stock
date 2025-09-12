CREATE TABLE IF NOT EXISTS index_compositions (
    date DATE NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    weight_percent DECIMAL(5, 2) NOT NULL,
    market_cap DECIMAL(20, 2) NOT NULL,
    price DECIMAL(18, 8) NOT NULL,
    return_percent DECIMAL(10, 4)
);

CREATE TABLE IF NOT EXISTS index_performance (
    date DATE NOT NULL,
    daily_return_percent DECIMAL(10, 4) NOT NULL,
    cumulative_return_percent DECIMAL(10, 4) NOT NULL,
    index_value DECIMAL(18, 8) NOT NULL,
    companies_count INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_compositions_date ON index_compositions(date);
CREATE INDEX IF NOT EXISTS idx_compositions_symbol ON index_compositions(symbol);
CREATE INDEX IF NOT EXISTS idx_performance_date ON index_performance(date);
