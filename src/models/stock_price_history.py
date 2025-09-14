from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, validator


class StockPriceHistory(BaseModel):
    id: Optional[str] = Field(None)
    company_symbol: str = Field(..., max_length=30)
    company_name: str = Field(..., max_length=100)
    last_traded_price: float = Field(...)
    market_cap: float = Field(...)
    one_day_return: float = Field(...)
    created_at: date = Field(...)
    
    @validator('last_traded_price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return round(v, 8)
    
    @validator('market_cap')
    def validate_market_cap(cls, v):
        if v <= 0:
            raise ValueError('Market cap must be positive')
        return round(v, 2)
    
    class Config:
        from_attributes = True


class StockPriceHistoryCreate(BaseModel):
    company_symbol: str = Field(..., max_length=30)
    company_name: str = Field(..., max_length=100)
    last_traded_price: float = Field(...)
    market_cap: float = Field(...)
    one_day_return: float = Field(...)
    created_at: date = Field(...)
    
    @validator('last_traded_price')
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError('Price must be positive')
        return round(v, 8)
    
    @validator('market_cap')
    def validate_market_cap(cls, v):
        if v <= 0:
            raise ValueError('Market cap must be positive')
        return round(v, 2)


class StockPriceHistoryResponse(BaseModel):
    id: str
    company_symbol: str
    company_name: str
    last_traded_price: float
    market_cap: float
    one_day_return: float
    created_at: date
    
    class Config:
        from_attributes = True