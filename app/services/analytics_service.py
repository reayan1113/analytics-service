"""Analytics service for reading from analytics tables"""
import logging
from typing import List, Optional
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from app.models.order import Order, OrderItem, OrderStatus
from app.models.analytics import DailyRevenueCache, HourlyOrderCache, ForecastHistory

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for reading analytics data from cache tables"""
    
    def __init__(self, order_db: Session, analytics_db: Session):
        """
        Initialize analytics service with both database sessions
        
        Args:
            order_db: Database session for order_db (read-only)
            analytics_db: Database session for analytics_db (read-write)
        """
        self.order_db = order_db
        self.analytics_db = analytics_db
    
    def get_daily_summaries(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None,
        limit: int = 30
    ) -> List[DailyRevenueCache]:
        """
        Get daily revenue summaries from cache
        
        Args:
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of records
            
        Returns:
            List of daily summaries
        """
        query = self.analytics_db.query(DailyRevenueCache)
        
        if start_date:
            query = query.filter(DailyRevenueCache.date >= start_date)
        if end_date:
            query = query.filter(DailyRevenueCache.date <= end_date)
        
        return query.order_by(desc(DailyRevenueCache.date)).limit(limit).all()
    
    def get_top_items(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[dict]:
        """
        Get top selling items (computed live from order data)
        
        Args:
            start_date: Start date filter (optional)
            end_date: End date filter (optional)
            limit: Maximum number of items
            
        Returns:
            List of top items with statistics
        """
        query = self.order_db.query(
            OrderItem.item_id,
            OrderItem.item_name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label('total_revenue')
        ).join(Order, OrderItem.order_id == Order.id)
        
        # Only count SERVED orders
        query = query.filter(Order.status == OrderStatus.SERVED)
        
        if start_date:
            query = query.filter(func.date(Order.created_at) >= start_date)
        if end_date:
            query = query.filter(func.date(Order.created_at) <= end_date)
        
        query = query.group_by(OrderItem.item_id, OrderItem.item_name)
        query = query.order_by(desc('total_quantity'))
        query = query.limit(limit)
        
        results = query.all()
        
        return [
            {
                'item_id': r.item_id,
                'item_name': r.item_name,
                'total_quantity': r.total_quantity,
                'total_revenue': r.total_revenue
            }
            for r in results
        ]
    
    def get_hourly_breakdown(
        self,
        target_date: Optional[date] = None,
        days_back: int = 7
    ) -> List[HourlyOrderCache]:
        """
        Get hourly order breakdown from cache
        
        Args:
            target_date: Specific date (defaults to today)
            days_back: Number of days to include
            
        Returns:
            List of hourly breakdowns
        """
        if not target_date:
            target_date = date.today()
        
        start_date = target_date - timedelta(days=days_back - 1)
        
        query = self.analytics_db.query(HourlyOrderCache)
        query = query.filter(
            and_(
                HourlyOrderCache.date >= start_date,
                HourlyOrderCache.date <= target_date
            )
        )
        query = query.order_by(HourlyOrderCache.date, HourlyOrderCache.hour)
        
        return query.all()
    
    def get_daily_forecasts(
        self,
        forecast_type: str = 'daily_revenue',
        limit: int = 7
    ) -> List[ForecastHistory]:
        """
        Get daily forecasts from history
        
        Args:
            forecast_type: Type of forecast
            limit: Maximum number of records
            
        Returns:
            List of forecast records
        """
        query = self.analytics_db.query(ForecastHistory)
        query = query.filter(ForecastHistory.forecast_type == forecast_type)
        query = query.order_by(desc(ForecastHistory.forecast_date))
        query = query.limit(limit)
        
        return query.all()
    
    def get_hourly_forecasts(
        self,
        forecast_date: Optional[date] = None
    ) -> List[ForecastHistory]:
        """
        Get hourly forecasts for a specific date
        
        Args:
            forecast_date: Target forecast date (defaults to tomorrow)
            
        Returns:
            List of hourly forecast records
        """
        if not forecast_date:
            forecast_date = date.today() + timedelta(days=1)
        
        query = self.analytics_db.query(ForecastHistory)
        query = query.filter(
            and_(
                ForecastHistory.forecast_type.like('hourly_%'),
                ForecastHistory.forecast_date == forecast_date
            )
        )
        query = query.order_by(ForecastHistory.forecast_type)
        
        return query.all()
