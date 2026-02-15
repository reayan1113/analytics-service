"""Pydantic schemas for API responses"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date
from decimal import Decimal


class DailySummary(BaseModel):
    """Daily revenue summary schema"""
    date: date
    total_revenue: Optional[Decimal] = Field(default=0, ge=0)
    order_count: Optional[int] = Field(default=0, ge=0)
    average_order_value: Optional[Decimal] = Field(default=0, ge=0)
    
    class Config:
        from_attributes = True


class TopItem(BaseModel):
    """Top selling item schema"""
    item_id: int
    item_name: str
    total_quantity: int
    total_revenue: Decimal
    
    class Config:
        from_attributes = True


class HourlyBreakdown(BaseModel):
    """Hourly order breakdown schema"""
    date: date
    hour: int = Field(ge=0, le=23)
    order_count: int = Field(ge=0)
    
    class Config:
        from_attributes = True


class DailyForecast(BaseModel):
    """Daily forecast schema"""
    forecast_date: date
    forecast_value: Decimal
    forecast_type: str
    
    class Config:
        from_attributes = True


class HourlyForecast(BaseModel):
    """Hourly forecast schema"""
    hour: int = Field(ge=0, le=23)
    forecast_value: Decimal
    
    class Config:
        from_attributes = True


class AnalyticsSummaryResponse(BaseModel):
    """Complete analytics summary response"""
    daily_summaries: List[DailySummary]
    total_records: int


class TopItemsResponse(BaseModel):
    """Top items response"""
    top_items: List[TopItem]
    total_items: int


class HourlyBreakdownResponse(BaseModel):
    """Hourly breakdown response"""
    hourly_data: List[HourlyBreakdown]
    total_records: int


class DailyForecastResponse(BaseModel):
    """Daily forecast response"""
    forecasts: List[DailyForecast]
    total_forecasts: int


class HourlyForecastResponse(BaseModel):
    """Hourly forecast response"""
    forecasts: List[HourlyForecast]
    total_forecasts: int
