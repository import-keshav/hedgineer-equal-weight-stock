import os
from datetime import date
from typing import List, Dict, Any, Optional
import aiohttp


class AlphaVantageClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALPHA_VANTAGE_API_KEY")
        self.base_url = "https://www.alphavantage.co/query"
    
    async def get_company_overview(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
            
        params = {
            'function': 'OVERVIEW',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
                    
                    if 'MarketCapitalization' in data:
                        return {
                            'symbol': symbol,
                            'market_cap': float(data.get('MarketCapitalization', 0)),
                            'name': data.get('Name', symbol),
                            'exchange': data.get('Exchange', 'Unknown')
                        }
        except Exception:
            return None
    
    async def get_daily_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
            
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': self.api_key
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as response:
                    data = await response.json()
                    
                    quote = data.get('Global Quote', {})
                    if quote:
                        return {
                            'symbol': quote.get('01. symbol'),
                            'price': float(quote.get('05. price', 0)),
                            'change_percent': quote.get('10. change percent', '0%').replace('%', ''),
                            'volume': int(quote.get('06. volume', 0))
                        }
        except Exception:
            return None
    
    async def get_top_stocks_by_market_cap(self, target_date: date, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        return []