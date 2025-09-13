import asyncio
import uuid
from datetime import date, datetime
from typing import List, Optional, Dict
from src.models.stock_price_history import StockPriceHistory, StockPriceHistoryCreate
from src.dtos.index_result import IndexComposition, IndexPerformance
from src.repositories.base_repository import BaseRepository


class StockPriceHistoryRepository:
    def __init__(self, base_repository: BaseRepository):
        self.base_repository = base_repository
    
    @property
    def connection(self):
        return self.base_repository.connection
    
    async def bulk_insert_stock_data(self, stock_data: List[StockPriceHistoryCreate]) -> int:
        if not stock_data:
            return 0
        
        target_date = stock_data[0].created_at
        delete_sql = "DELETE FROM stock_price_history WHERE created_at = ?;"
        
        try:
            await asyncio.to_thread(self.connection.execute, delete_sql, [target_date])
            
            insert_sql = """
            INSERT INTO stock_price_history 
            (id, company_symbol, company_name, last_traded_price, market_cap, one_day_return, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            
            for stock in stock_data:
                # Generate UUID for unique ID
                unique_id = str(uuid.uuid4())
                values = [
                    unique_id,
                    stock.company_symbol,
                    stock.company_name,
                    float(stock.last_traded_price),
                    float(stock.market_cap),
                    float(stock.one_day_return),
                    stock.created_at
                ]
                await asyncio.to_thread(self.connection.execute, insert_sql, values)
            
            return len(stock_data)
            
        except Exception:
            return 0
    
    async def get_stocks_by_date(self, target_date: date, limit: Optional[int] = None) -> List[StockPriceHistory]:
        try:
            if limit:
                query_sql = """
                SELECT id, company_symbol, company_name, last_traded_price, 
                       market_cap, one_day_return, created_at
                FROM stock_price_history 
                WHERE created_at = ?
                ORDER BY market_cap DESC
                LIMIT ?;
                """
                result = await asyncio.to_thread(
                    self.connection.execute, query_sql, [target_date, limit]
                )
            else:
                query_sql = """
                SELECT id, company_symbol, company_name, last_traded_price, 
                       market_cap, one_day_return, created_at
                FROM stock_price_history 
                WHERE created_at = ?
                ORDER BY market_cap DESC;
                """
                result = await asyncio.to_thread(
                    self.connection.execute, query_sql, [target_date]
                )
            
            rows = result.fetchall()
            return [
                StockPriceHistory(
                    id=row[0],
                    company_symbol=row[1],
                    company_name=row[2],
                    last_traded_price=float(row[3]),
                    market_cap=float(row[4]),
                    one_day_return=float(row[5]),
                    created_at=row[6]
                )
                for row in rows
            ]
        except Exception:
            return []
    
    async def get_top_stocks_by_date_range(self, start_date: date, end_date: date, limit: int = 100) -> Dict[date, List[StockPriceHistory]]:
        try:
            query_sql = """
            WITH ranked_stocks AS (
                SELECT 
                    id, company_symbol, company_name, last_traded_price, 
                    market_cap, one_day_return, created_at,
                    ROW_NUMBER() OVER (PARTITION BY created_at ORDER BY market_cap DESC) as rank
                FROM stock_price_history 
                WHERE created_at BETWEEN ? AND ?
            )
            SELECT 
                id, company_symbol, company_name, last_traded_price, 
                market_cap, one_day_return, created_at
            FROM ranked_stocks 
            WHERE rank <= ?
            ORDER BY created_at, market_cap DESC;
            """
            
            result = await asyncio.to_thread(
                self.connection.execute, query_sql, [start_date, end_date, limit]
            )
            
            rows = result.fetchall()
            
            stocks_by_date = {}
            for row in rows:
                stock = StockPriceHistory(
                    id=row[0],
                    company_symbol=row[1],
                    company_name=row[2],
                    last_traded_price=float(row[3]),
                    market_cap=float(row[4]),
                    one_day_return=float(row[5]),
                    created_at=row[6]
                )
                
                if stock.created_at not in stocks_by_date:
                    stocks_by_date[stock.created_at] = []
                stocks_by_date[stock.created_at].append(stock)
            
            return stocks_by_date
            
        except Exception:
            return {}
    
    async def get_available_dates(self) -> List[date]:
        query_sql = "SELECT DISTINCT created_at FROM stock_price_history ORDER BY created_at DESC;"
        
        try:
            result = await asyncio.to_thread(self.connection.execute, query_sql)
            rows = result.fetchall()
            return [row[0] for row in rows]
        except Exception:
            return []
    
    async def get_stocks_count_by_date(self, target_date: date) -> int:
        query_sql = "SELECT COUNT(*) FROM stock_price_history WHERE created_at = ?;"
        
        try:
            result = await asyncio.to_thread(
                self.connection.execute, query_sql, [target_date]
            )
            row = result.fetchone()
            return row[0] if row else 0
        except Exception:
            return 0
    
    async def insert_index_composition(self, compositions: List[IndexComposition]) -> bool:
        """Insert index composition data (does not handle existing data)"""
        try:
            for comp in compositions:
                insert_sql = """
                INSERT INTO index_compositions 
                (id, date, symbol, company_name, weight_percent, market_cap, price, return_percent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
                # Generate UUID for unique ID
                unique_id = str(uuid.uuid4())
                await asyncio.to_thread(self.connection.execute, insert_sql, [
                    unique_id, comp.date, comp.symbol, comp.company_name, comp.weight_percent,
                    comp.market_cap, comp.price, comp.return_percent
                ])
            return True
        except Exception:
            return False

    async def insert_index_performance(self, performance: List[IndexPerformance]) -> bool:
        """Insert index performance data (does not handle existing data)"""
        try:
            for perf in performance:
                insert_sql = """
                INSERT INTO index_performance 
                (id, date, daily_return_percent, cumulative_return_percent, index_value, companies_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """
                # Generate UUID for unique ID
                unique_id = str(uuid.uuid4())
                values = [unique_id, perf.date, perf.daily_return_percent, perf.cumulative_return_percent, perf.index_value, perf.companies_count]
                await asyncio.to_thread(self.connection.execute, insert_sql, values)
            
            return True
        except Exception:
            return False

    async def get_persisted_index_composition(self, target_date: date) -> List[IndexComposition]:
        try:
            query_sql = """
            SELECT date, symbol, company_name, weight_percent, market_cap, price, return_percent
            FROM index_compositions 
            WHERE date = ?
            ORDER BY market_cap DESC
            """
            result = await asyncio.to_thread(self.connection.execute, query_sql, [target_date])
            rows = result.fetchall()
            return [
                IndexComposition(
                    date=row[0],
                    symbol=row[1],
                    company_name=row[2],
                    weight_percent=float(row[3]),
                    market_cap=float(row[4]),
                    price=float(row[5]),
                    return_percent=float(row[6])
                )
                for row in rows
            ]
        except Exception:
            return []

    async def get_persisted_index_performance(self, start_date: date, end_date: date) -> List[IndexPerformance]:
        try:
            query_sql = """
            SELECT date, daily_return_percent, cumulative_return_percent, index_value, companies_count
            FROM index_performance 
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC
            """
            result = await asyncio.to_thread(self.connection.execute, query_sql, [start_date, end_date])
            rows = result.fetchall()
            
            return [
                IndexPerformance(
                    date=row[0],
                    daily_return_percent=float(row[1]),
                    cumulative_return_percent=float(row[2]),
                    index_value=float(row[3]),
                    companies_count=int(row[4])
                )
                for row in rows
            ]
        except Exception:
            return []

    async def get_last_built_date(self) -> Optional[date]:
        try:
            query_sql = "SELECT MAX(date) FROM index_performance"
            result = await asyncio.to_thread(self.connection.execute, query_sql)
            row = result.fetchone()
            return row[0] if row and row[0] else None
        except Exception:
            return None
