from datetime import date, datetime, timedelta
from typing import List, Optional
from src.services.stock_history_service import StockHistoryService
from src.constants import TOP_COMPANIES_COUNT
from src.dtos.operation_result import OperationResult, DataSummary, ValidationResult, ReturnStats, StockSummary


class IndexDataDumpManager:
    def __init__(self, stock_history_service: StockHistoryService):
        self.stock_history_service = stock_history_service
    
    async def run_daily_dump(self, target_date: Optional[date] = None) -> OperationResult:
        if target_date is None:
            target_date = date.today()
        
        start_time = datetime.now()
        
        try:
            records_stored = await self.stock_history_service.fetch_and_store_top_stocks(target_date)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return OperationResult(
                success=True,
                operation="daily_dump",
                date=target_date,
                records_processed=records_stored,
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return OperationResult(
                success=False,
                operation="daily_dump",
                date=target_date,
                records_processed=0,
                execution_time_seconds=execution_time,
                error_message=str(e)
            )
    
    async def run_backfill(self, start_date: date, end_date: Optional[date] = None) -> List[OperationResult]:
        if end_date is None:
            end_date = start_date
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            if current_date.weekday() >= 5:
                current_date += timedelta(days=1)
                continue
            
            result = await self.run_daily_dump(current_date)
            results.append(result)
            current_date += timedelta(days=1)
        
        return results
    
    async def validate_data(self, target_date: date) -> ValidationResult:
        try:
            stock_count = await self.stock_history_service.get_stocks_count_by_date(target_date)
            
            return ValidationResult(
                date=target_date,
                is_valid=stock_count == TOP_COMPANIES_COUNT,
                expected_count=TOP_COMPANIES_COUNT,
                actual_count=stock_count,
                has_data=stock_count > 0
            )
            
        except Exception:
            return ValidationResult(
                date=target_date,
                is_valid=False,
                expected_count=TOP_COMPANIES_COUNT,
                actual_count=0,
                has_data=False
            )
    
    async def get_available_dates(self) -> List[date]:
        try:
            return await self.stock_history_service.get_available_dates()
        except Exception:
            return []