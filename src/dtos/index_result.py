from datetime import date
from typing import List, Optional
from pydantic import BaseModel


class IndexComposition(BaseModel):
    date: date
    symbol: str
    company_name: str
    weight_percent: float = 1.0
    market_cap: float
    price: float
    return_percent: float


class IndexPerformance(BaseModel):
    date: date
    daily_return_percent: float
    cumulative_return_percent: float
    index_value: float
    companies_count: int


class CompositionChange(BaseModel):
    date: date
    symbol: str
    company_name: str
    change_type: str
    previous_weight_percent: float
    new_weight_percent: float


class IndexBuildResult(BaseModel):
    start_date: date
    end_date: date
    trading_days: int
    total_compositions_built: int
    success: bool
    error_message: Optional[str] = None
