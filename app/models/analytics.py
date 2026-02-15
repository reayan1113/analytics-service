"""
Analytics tables - created and managed by Analytics Service
"""
from sqlalchemy import Column, BigInteger, Date, Integer, Numeric, String, TIMESTAMP, UniqueConstraint, text
from app.database import AnalyticsBase


class DailyRevenueCache(AnalyticsBase):
    """Cache for daily revenue analytics"""
    __tablename__ = "daily_revenue_cache"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, unique=True, nullable=False, index=True)
    total_revenue = Column(Numeric(10, 2))
    order_count = Column(Integer)
    average_order_value = Column(Numeric(10, 2))
    created_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))


class HourlyOrderCache(AnalyticsBase):
    """Cache for hourly order statistics"""
    __tablename__ = "hourly_order_cache"
    __table_args__ = (
        UniqueConstraint('date', 'hour', name='unique_date_hour'),
    )
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    date = Column(Date, nullable=False, index=True)
    hour = Column(Integer, nullable=False)
    order_count = Column(Integer)


class ForecastHistory(AnalyticsBase):
    """History of generated forecasts"""
    __tablename__ = "forecast_history"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    forecast_type = Column(String(50), nullable=False, index=True)
    forecast_value = Column(Numeric(10, 2))
    forecast_date = Column(Date, nullable=False, index=True)
    generated_at = Column(TIMESTAMP, server_default=text('CURRENT_TIMESTAMP'))
