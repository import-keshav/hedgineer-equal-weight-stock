import logging
from datetime import date
from typing import List, Dict
from src.repositories.stock_price_history_repository import StockPriceHistoryRepository
from src.constants import TOP_COMPANIES_COUNT
from src.dtos.index_result import IndexComposition, IndexPerformance

logger = logging.getLogger(__name__)


class IndexService:
    def __init__(self, repository: StockPriceHistoryRepository):
        self.repository = repository
        
    async def get_index_composition(self, target_date: date) -> List[IndexComposition]:
        stocks = await self.repository.get_stocks_by_date(target_date, TOP_COMPANIES_COUNT)
        
        if not stocks:
            return []
            
        weight_per_stock = 100.0 / len(stocks)
        
        composition = [
            IndexComposition(
                date=target_date,
                symbol=stock.company_symbol,
                company_name=stock.company_name,
                weight_percent=weight_per_stock,
                market_cap=stock.market_cap,
                price=stock.last_traded_price,
                return_percent=stock.one_day_return
            )
            for stock in stocks
        ]
        
        return composition
    
    async def get_index_composition_for_date_range(self, start_date: date, end_date: date) -> Dict[date, List[IndexComposition]]:
        stocks_by_date = await self.repository.get_top_stocks_by_date_range(start_date, end_date, TOP_COMPANIES_COUNT)
        
        composition_by_date = {}
        
        for target_date, stocks in stocks_by_date.items():
            if stocks:
                weight_per_stock = 100.0 / len(stocks)
                
                composition = [
                    IndexComposition(
                        date=target_date,
                        symbol=stock.company_symbol,
                        company_name=stock.company_name,
                        weight_percent=weight_per_stock,
                        market_cap=stock.market_cap,
                        price=stock.last_traded_price,
                        return_percent=stock.one_day_return
                    )
                    for stock in stocks
                ]
                
                composition_by_date[target_date] = composition
        
        return composition_by_date
    
    async def get_persisted_index_composition(self, target_date: date) -> List[IndexComposition]:
        """Get persisted index composition for a specific date"""
        return await self.repository.get_persisted_index_composition(target_date)
    
    async def get_persisted_index_performance(self, start_date: date, end_date: date) -> List[IndexPerformance]:
        """Get persisted index performance for a date range"""
        return await self.repository.get_persisted_index_performance(start_date, end_date)
    
    async def persist_index_composition(self, compositions: List[IndexComposition]) -> None:
        """Persist index compositions to database (only inserts new data, skips existing)"""
        if not compositions:
            return
        
        # Business logic: Only persist data for dates that don't already exist
        # Group by date to check existence efficiently
        compositions_by_date = {}
        for comp in compositions:
            if comp.date not in compositions_by_date:
                compositions_by_date[comp.date] = []
            compositions_by_date[comp.date].append(comp)
        
        new_compositions = []
        for target_date, date_compositions in compositions_by_date.items():
            existing = await self.repository.get_persisted_index_composition(target_date)
            if not existing:  # Only add if no data exists for this date
                new_compositions.extend(date_compositions)
        
        if new_compositions:
            await self.repository.insert_index_composition(new_compositions)
    
    async def persist_index_performance(self, performance: List[IndexPerformance]) -> None:
        """Persist index performance to database (only inserts new data, skips existing)"""
        if not performance:
            return
        
        # Business logic: Only persist data for dates that don't already exist
        # Check all dates at once for efficiency
        all_dates = [perf.date for perf in performance]
        start_date = min(all_dates)
        end_date = max(all_dates)
        existing_performance = await self.repository.get_persisted_index_performance(start_date, end_date)
        existing_dates = set(perf.date for perf in existing_performance)
        
        new_performance = [perf for perf in performance if perf.date not in existing_dates]
        
        if new_performance:
            await self.repository.insert_index_performance(new_performance)