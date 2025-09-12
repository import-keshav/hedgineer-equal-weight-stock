from datetime import date
from typing import List, Dict, Any
from src.clients.yahoo_finance_client import YahooFinanceClient
from src.clients.alpha_vantage_client import AlphaVantageClient


class DataSourceService:
    def __init__(self):
        self.yahoo_client = YahooFinanceClient()
        self.alpha_vantage_client = AlphaVantageClient()
        self.primary_source = "yahoo_finance"
        self.secondary_source = "alpha_vantage"
    
    async def get_top_stocks_by_market_cap(self, target_date: date, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            primary_data = await self.yahoo_client.get_top_stocks_by_market_cap(target_date, limit)
            if primary_data and len(primary_data) >= limit * 0.8:
                for stock in primary_data:
                    stock['data_source'] = self.primary_source
                return primary_data[:limit]
        except Exception:
            pass
        
        try:
            secondary_data = await self.alpha_vantage_client.get_top_stocks_by_market_cap(target_date, limit)
            if secondary_data and len(secondary_data) >= limit * 0.5:
                for stock in secondary_data:
                    stock['data_source'] = self.secondary_source
                return secondary_data[:limit]
        except Exception:
            pass
        
        raise Exception("All data sources unavailable")
    
