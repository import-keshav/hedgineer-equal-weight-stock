import asyncio
import requests
from datetime import date, timedelta, datetime
from typing import List, Dict, Any, Optional
import pandas as pd
import time
from urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)


class YahooFinanceClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < 0.02:  # Minimal rate limiting - 0.02 seconds (50 requests/second)
            time.sleep(0.02 - time_since_last)
        self.last_request_time = time.time()
    
    async def get_sp500_symbols(self) -> List[str]:
        def _fetch_sp500_symbols():
            try:
                url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
                response = self.session.get(url)
                tables = pd.read_html(response.content)
                symbols = tables[0]['Symbol'].tolist()
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
            self._rate_limit()
            
            start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())
            end_timestamp = int(datetime.combine(end_date + timedelta(days=1), datetime.min.time()).timestamp())
            
            chart_url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
            chart_params = {
                'period1': start_timestamp,
                'period2': end_timestamp,
                'interval': '1d',
                'includePrePost': 'false',
                'events': 'div,splits'
            }
            
            chart_response = self.session.get(chart_url, params=chart_params, timeout=10)
            
            if chart_response.status_code != 200:
                return None
            
            chart_data = chart_response.json()
            
            if 'chart' not in chart_data or not chart_data['chart']['result']:
                return None
            
            result = chart_data['chart']['result'][0]
            
            if not result.get('timestamp') or not result.get('indicators', {}).get('quote'):
                return None
            
            quotes = result['indicators']['quote'][0]
            
            if not quotes.get('close'):
                return None
            
            latest_close = quotes['close'][-1]
            latest_volume = quotes.get('volume', [0])[-1] or 0
            
            if latest_close is None:
                return None
            
            one_day_return = 0.0
            if len(quotes['close']) >= 2 and quotes['close'][-2] is not None:
                previous_close = quotes['close'][-2]
                if previous_close > 0:
                    one_day_return = ((latest_close - previous_close) / previous_close) * 100
            
            company_name = symbol
            market_cap = 0.0
            
            try:
                info_url = f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{symbol}"
                info_params = {'modules': 'price,summaryDetail'}
                
                info_response = self.session.get(info_url, params=info_params, timeout=8)
                
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    
                    if 'quoteSummary' in info_data and info_data['quoteSummary']['result']:
                        quote_summary = info_data['quoteSummary']['result'][0]
                        
                        if 'price' in quote_summary:
                            price_info = quote_summary['price']
                            company_name = price_info.get('longName', price_info.get('shortName', symbol))
                        
                        if 'summaryDetail' in quote_summary and 'marketCap' in quote_summary['summaryDetail']:
                            market_cap_data = quote_summary['summaryDetail']['marketCap']
                            if isinstance(market_cap_data, dict) and 'raw' in market_cap_data:
                                market_cap = float(market_cap_data['raw'])
                            
            except Exception:
                if latest_volume > 0:
                    estimated_shares = latest_volume * 100
                    market_cap = estimated_shares * latest_close
            
            if market_cap == 0.0 and latest_volume > 0:
                estimated_shares = latest_volume * 200
                market_cap = estimated_shares * latest_close
            
            if len(company_name) > 100:
                company_name = company_name[:97] + "..."
            
            return {
                'symbol': symbol,
                'company_name': company_name,
                'last_traded_price': float(latest_close),
                'market_cap': float(market_cap),
                'one_day_return': float(one_day_return),
                'date': end_date,
                'volume': float(latest_volume)
            }
            
        except Exception:
            return None
    
    async def _fetch_batch_stock_data(self, symbols: List[str], start_date: date, end_date: date) -> List[Dict[str, Any]]:
        async def fetch_single_async(symbol: str) -> Optional[Dict[str, Any]]:
            try:
                result = await asyncio.to_thread(self._fetch_single_stock_data, symbol, start_date, end_date)
                return result if result and result.get('market_cap', 0) > 0 else None
            except Exception:
                return None
        
        semaphore = asyncio.Semaphore(10)  # Increased concurrency for better performance
        
        async def fetch_with_semaphore(symbol: str) -> Optional[Dict[str, Any]]:
            async with semaphore:
                return await fetch_single_async(symbol)
        
        try:
            tasks = [fetch_with_semaphore(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            valid_results = []
            for result in results:
                if result and not isinstance(result, Exception):
                    valid_results.append(result)
            
            return valid_results
            
        except Exception:
            return []
    
    async def fetch_stocks_data(self, symbols: List[str], target_date: date, days_back: int = 5) -> List[Dict[str, Any]]:
        start_date = target_date - timedelta(days=days_back)
        end_date = target_date
        
        batch_size = 20  # Optimal batch size for 500 symbols
        all_results = []
        
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i + batch_size]
            
            try:
                batch_results = await self._fetch_batch_stock_data(batch_symbols, start_date, end_date)
                all_results.extend(batch_results)
            except Exception:
                continue
            
            # Minimal delay between batches
            if i + batch_size < len(symbols):
                await asyncio.sleep(0.1)
        
        return all_results
    
    async def get_top_stocks_by_market_cap(self, target_date: date, limit: int = 100, days_back: int = 5) -> List[Dict[str, Any]]:
        try:
            selected_symbols = await self.get_sp500_symbols()
            
            if not selected_symbols:
                # Fallback list of top companies by market cap (manually curated)
                selected_symbols = [
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
                    'LLY', 'ORCL', 'CCI', 'AMT', 'PYPL', 'NFLX', 'ADBE', 'CMCSA',
                    'PEP', 'T', 'VZ', 'MRK', 'ABT', 'COST', 'TMO', 'DHR', 'NEE',
                    'UNP', 'LIN', 'PM', 'LOW', 'UPS', 'QCOM', 'RTX', 'HON', 'SBUX',
                    'CAT', 'DE', 'AXP', 'GE', 'IBM', 'GS', 'BA', 'MMM', 'WMT',
                    'JNJ', 'PG', 'KO', 'MCD', 'CVX', 'XOM', 'HD', 'MA', 'V'
                ]
          
            all_stocks_data = await self.fetch_stocks_data(selected_symbols, target_date, days_back)
            
            valid_stocks = [
                stock for stock in all_stocks_data 
                if stock['market_cap'] > 0 and stock['last_traded_price'] > 0
            ]
            
            sorted_stocks = sorted(valid_stocks, key=lambda x: x['market_cap'], reverse=True)[:limit]
            
            return sorted_stocks
            
        except Exception:
            return []