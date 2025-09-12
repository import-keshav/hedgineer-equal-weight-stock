import io
from datetime import date, timedelta
from typing import List, Dict, Optional
import pandas as pd
from src.services.index_service import IndexService
from src.services.redis_service import RedisService
from src.constants import TOP_COMPANIES_COUNT
from src.dtos.index_result import IndexComposition, IndexPerformance, CompositionChange, IndexBuildResult


class IndexManager:
    def __init__(self, index_service: IndexService, redis_service: RedisService):
        self.index_service = index_service
        self.redis_service = redis_service
    
    async def get_index_performance(self, start_date: date, end_date: date) -> List[IndexPerformance]:
        cached_data = await self.redis_service.get_index_performance(start_date, end_date)
        if cached_data:
            return [IndexPerformance.model_validate(item) for item in cached_data]
        
        performance_data = await self.index_service.repository.get_persisted_index_performance(start_date, end_date)
        
        if performance_data:
            serializable_data = [perf.model_dump() for perf in performance_data]
            await self.redis_service.set_index_performance(start_date, end_date, serializable_data)
        
        return performance_data
    
    async def get_index_composition(self, target_date: date) -> List[IndexComposition]:
        cached_data = await self.redis_service.get_index_composition(target_date)
        if cached_data:
            return [IndexComposition.model_validate(item) for item in cached_data]
        
        composition_data = await self.index_service.repository.get_persisted_index_composition(target_date)
        
        if composition_data:
            serializable_data = [comp.model_dump() for comp in composition_data]
            await self.redis_service.set_index_composition(target_date, serializable_data)
        
        return composition_data
    
    async def get_composition_changes(self, start_date: date, end_date: date) -> List[CompositionChange]:
        cached_data = await self.redis_service.get_composition_changes(start_date, end_date)
        if cached_data:
            return [CompositionChange.model_validate(item) for item in cached_data]
        
        changes = []
        current_date = start_date
        previous_symbols = set()
        
        while current_date <= end_date:
            if current_date.weekday() < 5:
                composition = await self.index_service.repository.get_persisted_index_composition(current_date)
                
                if composition:
                    current_symbols = {stock.symbol for stock in composition}
                    
                    if previous_symbols:
                        entered = current_symbols - previous_symbols
                        exited = previous_symbols - current_symbols
                        for symbol in entered:
                            stock = next(s for s in composition if s.symbol == symbol)
                            changes.append(CompositionChange(
                                date=current_date,
                                symbol=symbol,
                                company_name=stock.company_name,
                                change_type="entered",
                                previous_weight_percent=0.0,
                                new_weight_percent=stock.weight_percent
                            ))
                        
                        for symbol in exited:
                            changes.append(CompositionChange(
                                date=current_date,
                                symbol=symbol,
                                company_name="Unknown",
                                change_type="exited",
                                previous_weight_percent=100.0 / TOP_COMPANIES_COUNT,
                                new_weight_percent=0.0
                            ))
                    
                    previous_symbols = current_symbols
            
            current_date += timedelta(days=1)
        
        if changes:
            serializable_data = [change.model_dump() for change in changes]
            await self.redis_service.set_composition_changes(start_date, end_date, serializable_data)
        
        return changes
    
    async def export_to_excel(self, start_date: date, end_date: Optional[date] = None) -> io.BytesIO:
        if end_date is None:
            end_date = start_date
            
        excel_buffer = io.BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            performance_data = await self.get_index_performance(start_date, end_date)
            if performance_data:
                perf_df = pd.DataFrame([
                    {
                        'Date': p.date,
                        'Daily Return (%)': p.daily_return_percent,
                        'Cumulative Return (%)': p.cumulative_return_percent,
                        'Index Value': p.index_value,
                        'Companies Count': p.companies_count
                    }
                    for p in performance_data
                ])
                perf_df.to_excel(writer, sheet_name='Index Performance', index=False)
            
            latest_composition = await self.get_index_composition(end_date)
            if latest_composition:
                comp_df = pd.DataFrame([
                    {
                        'Symbol': c.symbol,
                        'Company Name': c.company_name,
                        'Weight (%)': c.weight_percent,
                        'Market Cap': c.market_cap,
                        'Stock Price': c.price,
                        'Return (%)': c.return_percent
                    }
                    for c in latest_composition
                ])
                comp_df.to_excel(writer, sheet_name=f'Composition {end_date}', index=False)
            
            changes_data = await self.get_composition_changes(start_date, end_date)
            if changes_data:
                changes_df = pd.DataFrame([
                    {
                        'Date': c.date,
                        'Symbol': c.symbol,
                        'Company Name': c.company_name,
                        'Change Type': c.change_type,
                        'Previous Weight (%)': c.previous_weight_percent,
                        'New Weight (%)': c.new_weight_percent
                    }
                    for c in changes_data
                ])
                changes_df.to_excel(writer, sheet_name='Composition Changes', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer
