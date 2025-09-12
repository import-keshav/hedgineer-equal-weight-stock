import asyncio
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed


class YahooFinanceClient:
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
    
    async def get_sp500_symbols(self) -> List[str]:
        def _fetch_sp500_symbols():
            try:
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                tables = pd.read_html(url)
                sp500_table = tables[0]
                symbols = sp500_table['Symbol'].tolist()
                return [str(symbol).replace('.', '-') for symbol in symbols]
            except Exception:
                return [
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
                    'NOW', 'CL', 'FCX', 'GS', 'MCO', 'TGT', 'F', 'GM', 'SPG', 'APD'
                ]
        
        return await asyncio.to_thread(_fetch_sp500_symbols)
    
    def _fetch_single_stock_data(self, symbol: str, start_date: date, end_date: date) -> Optional[Dict[str, Any]]:
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))
            
            if hist.empty:
                return None
            
            latest_data = hist.iloc[-1]
            info = ticker.info
            
            shares_outstanding = info.get('sharesOutstanding') or info.get('impliedSharesOutstanding')
            market_cap = None
            
            if shares_outstanding and latest_data['Close']:
                market_cap = shares_outstanding * latest_data['Close']
            elif info.get('marketCap'):
                market_cap = info.get('marketCap')
            
            one_day_return = 0.0
            if len(hist) >= 2:
                previous_close = hist.iloc[-2]['Close']
                current_close = latest_data['Close']
                one_day_return = ((current_close - previous_close) / previous_close) * 100
            
            company_name = info.get('longName') or info.get('shortName') or symbol
            if len(company_name) > 100:
                company_name = company_name[:97] + "..."
            
            return {
                'symbol': symbol,
                'company_name': company_name,
                'last_traded_price': float(latest_data['Close']),
                'market_cap': float(market_cap) if market_cap else 0.0,
                'one_day_return': float(one_day_return),
                'date': end_date,
                'volume': float(latest_data.get('Volume', 0))
            }
            
        except Exception:
            return None
    
    async def fetch_stocks_data(self, symbols: List[str], target_date: date, days_back: int = 5) -> List[Dict[str, Any]]:
        start_date = target_date - timedelta(days=days_back)
        end_date = target_date
        
        def _fetch_batch(symbol_batch: List[str]) -> List[Dict[str, Any]]:
            results = []
            for symbol in symbol_batch:
                try:
                    result = self._fetch_single_stock_data(symbol, start_date, end_date)
                    if result and result['market_cap'] > 0:
                        results.append(result)
                except Exception:
                    continue
            return results
        
        batch_size = max(1, len(symbols) // self.max_workers)
        symbol_batches = [symbols[i:i + batch_size] for i in range(0, len(symbols), batch_size)]
        
        all_results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(_fetch_batch, batch): batch 
                for batch in symbol_batches
            }
            
            for future in as_completed(future_to_batch):
                try:
                    batch_results = future.result(timeout=30)
                    all_results.extend(batch_results)
                except Exception:
                    continue
        
        return all_results
    
    async def get_top_stocks_by_market_cap(self, target_date: date, limit: int = 100, days_back: int = 5) -> List[Dict[str, Any]]:
        symbols = await self.get_sp500_symbols()
        all_stocks_data = await self.fetch_stocks_data(symbols, target_date, days_back)
        valid_stocks = [
            stock for stock in all_stocks_data 
            if stock['market_cap'] > 0 and stock['last_traded_price'] > 0
        ]
        return sorted(valid_stocks, key=lambda x: x['market_cap'], reverse=True)[:limit]