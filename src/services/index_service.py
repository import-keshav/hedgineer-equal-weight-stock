import logging
from datetime import date
from typing import List, Dict
from src.repositories.stock_price_history_repository import StockPriceHistoryRepository
from src.constants import TOP_COMPANIES_COUNT
from src.dtos.index_result import IndexComposition

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