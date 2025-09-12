from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class OperationResult(BaseModel):
    success: bool
    operation: str
    date: date
    records_processed: int = 0
    execution_time_seconds: float = 0.0
    error_message: Optional[str] = None


class ReturnStats(BaseModel):
    average_return_percent: float
    max_return_percent: float  
    min_return_percent: float


class StockSummary(BaseModel):
    symbol: str
    name: str
    market_cap: float
    price: float
    return_percent: float


class DataSummary(BaseModel):
    has_data: bool
    total_dates: int
    earliest_date: Optional[date] = None
    latest_date: Optional[date] = None
    data_coverage_percent: float = 0.0
    sample_stocks: List[StockSummary] = []
    return_stats: Optional[ReturnStats] = None


class ValidationResult(BaseModel):
    is_valid: bool
    date: date
    total_records: int = 0
    validation_errors: List[str] = []
