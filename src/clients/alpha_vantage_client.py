import os
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)


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
    
    async def get_stock_data(self, symbol: str, target_date: date) -> Optional[Dict[str, Any]]:
        try:
            overview, quote = await asyncio.gather(
                self.get_company_overview(symbol),
                self.get_daily_quote(symbol)
            )
            
            if overview and quote:
                return {
                    'symbol': symbol,
                    'company_name': overview.get('name', symbol),
                    'last_traded_price': quote.get('price', 0),
                    'market_cap': overview.get('market_cap', 0),
                    'one_day_return': float(quote.get('change_percent', 0)),
                    'date': target_date,
                    'volume': quote.get('volume', 0)
                }
        except Exception:
            pass
        return None
    
    async def get_top_stocks_by_market_cap(self, target_date: date, limit: int = 100) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        
        large_cap_symbols = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B',
            'UNH', 'JNJ', 'JPM', 'V', 'PG', 'XOM', 'HD', 'CVX', 'MA', 'PFE',
            'ABBV', 'BAC', 'COST', 'KO', 'AVGO', 'WMT', 'DIS', 'TMO', 'PEP',
            'MRK', 'ABT', 'CSCO', 'ACN', 'LIN', 'DHR', 'VZ', 'ADBE', 'CRM',
            'NFLX', 'CMCSA', 'NKE', 'INTC', 'TXN', 'AMD', 'QCOM', 'PM', 'WFC',
            'UPS', 'RTX', 'LOW', 'HON', 'SPGI', 'NEE', 'IBM', 'AMGN', 'CAT',
            'BA', 'SBUX', 'BLK', 'GE', 'AXP', 'MDT', 'DE', 'ELV', 'BKNG',
            'GILD', 'MCD', 'MMM', 'CVS', 'ADP', 'TJX', 'VRTX', 'SYK', 'MDLZ',
            'ZTS', 'LRCX', 'CB', 'ISRG', 'C', 'SO', 'TMUS', 'MO', 'ADI',
            'DUK', 'PLD', 'CI', 'SCHW', 'FIS', 'EMR', 'SHW', 'BSX', 'ICE',
            'ITW', 'BDX', 'NSC', 'COP', 'MMC', 'AON', 'USB', 'EQIX', 'WM',
            'NOW', 'CL', 'FCX', 'GS', 'MCO', 'TGT', 'F', 'GM', 'SPG', 'APD',
            'PYPL', 'GPN', 'LMT', 'ORCL', 'BDX', 'ETN', 'REGN', 'INTU', 'FISV',
            'PNC', 'D', 'CME', 'FDX', 'PSA', 'CCI', 'SLB', 'MS', 'BMY', 'HCA'
        ]
        
        results = []
        batch_size = 2
        
        for i in range(0, len(large_cap_symbols), batch_size):
            batch = large_cap_symbols[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.get_stock_data(symbol, target_date) for symbol in batch]
            )
            
            for result in batch_results:
                if result and result['market_cap'] > 0:
                    results.append(result)
            
            if len(results) >= limit * 1.5:
                break
            
            if i + batch_size < len(large_cap_symbols):
                await asyncio.sleep(12)
        
        valid_stocks = [
            stock for stock in results 
            if stock['market_cap'] > 0 and stock['last_traded_price'] > 0
        ]
        
        return sorted(valid_stocks, key=lambda x: x['market_cap'], reverse=True)[:limit]