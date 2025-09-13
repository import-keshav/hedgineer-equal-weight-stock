from datetime import date
from typing import List, Optional
from src.services.data_source_service import DataSourceService
from src.repositories.stock_price_history_repository import StockPriceHistoryRepository
from src.models.stock_price_history import StockPriceHistory, StockPriceHistoryCreate
from src.constants import TOP_COMPANIES_COUNT
import logging

logger = logging.getLogger(__name__)


class StockHistoryService:
    def __init__(self, data_source_service: DataSourceService, repository: StockPriceHistoryRepository):
        self.data_source_service = data_source_service
        self.repository: StockPriceHistoryRepository = repository
    
    async def fetch_and_store_top_stocks(self, target_date: date) -> int:
        existing_data = await self.repository.get_stocks_by_date(target_date)
        if existing_data:
            return len(existing_data)
        
        stock_data = await self.data_source_service.get_top_stocks_by_market_cap(
            target_date=target_date,
            limit=TOP_COMPANIES_COUNT
        )
        
        if not stock_data:
            return 0
        
        stock_models = []
        for stock in stock_data:
            try:
                stock_model = StockPriceHistoryCreate(
                    company_symbol=stock['symbol'],
                    company_name=stock['company_name'],
                    last_traded_price=stock['last_traded_price'],
                    market_cap=stock['market_cap'],
                    one_day_return=stock['one_day_return'],
                    created_at=target_date
                )
                stock_models.append(stock_model)
            except Exception:
                continue
        
        result = await self.repository.bulk_insert_stock_data(stock_models)
        return result
    
    async def get_stocks_for_date(self, target_date: date, limit: Optional[int] = None) -> List[StockPriceHistory]:
        return await self.repository.get_stocks_by_date(target_date, limit)
    
    async def get_available_dates(self) -> List[date]:
        return await self.repository.get_available_dates()
    
    async def get_stocks_count_by_date(self, target_date: date) -> int:
        """Get count of stocks for a specific date"""
        return await self.repository.get_stocks_count_by_date(target_date)