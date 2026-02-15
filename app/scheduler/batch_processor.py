"""
Scheduled batch processor for computing analytics at midnight
Runs in a separate thread with APScheduler
"""
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Tuple
from sqlalchemy import func, and_, extract
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import threading

import app.database as database
from app.models.order import Order, OrderStatus
from app.models.analytics import DailyRevenueCache, HourlyOrderCache, ForecastHistory
from app.services.forecasting_service import ForecastingService
from app.config import config

logger = logging.getLogger(__name__)

# Lock to prevent duplicate runs
batch_lock = threading.Lock()


class BatchProcessor:
    """Midnight batch processor for analytics computation"""
    
    def __init__(self):
        self.scheduler = None
        self.forecasting_service = ForecastingService()
        self.is_running = False
    
    def start(self):
        """Start the scheduler"""
        if not config.scheduler_enabled:
            logger.info("Scheduler is disabled in configuration")
            return
        
        if self.scheduler is not None:
            logger.warning("Scheduler already running")
            return
        
        logger.info("Starting analytics batch scheduler")
        
        self.scheduler = BackgroundScheduler()
        
        # Parse run time from config (format: "HH:MM")
        try:
            hour, minute = map(int, config.scheduler_run_time.split(':'))
        except ValueError:
            logger.error(f"Invalid scheduler run_time format: {config.scheduler_run_time}")
            hour, minute = 0, 0
        
        # Schedule the batch job
        self.scheduler.add_job(
            func=self.run_batch_job,
            trigger=CronTrigger(hour=hour, minute=minute),
            id='midnight_batch',
            name='Midnight Analytics Batch Process',
            replace_existing=True
        )
        
        self.scheduler.start()
        logger.info(f"Scheduler started - will run daily at {hour:02d}:{minute:02d}")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler:
            logger.info("Stopping analytics batch scheduler")
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
    
    def run_batch_job(self):
        """
        Main batch job execution
        Computes all analytics and forecasts
        """
        # Acquire lock to prevent duplicate runs
        if not batch_lock.acquire(blocking=False):
            logger.warning("Batch job already running, skipping")
            return
        
        try:
            self.is_running = True
            logger.info("=" * 60)
            logger.info("STARTING MIDNIGHT BATCH PROCESS")
            logger.info(f"Execution time: {datetime.now()}")
            logger.info("=" * 60)
            
            # Create database sessions for both databases
            order_db = database.OrderSessionLocal()
            analytics_db = database.AnalyticsSessionLocal()
            
            try:
                # Compute yesterday's analytics (full day data)
                yesterday = date.today() - timedelta(days=1)
                
                # 1. Compute and store daily revenue
                self._compute_daily_revenue(order_db, analytics_db, yesterday)
                
                # 2. Compute and store hourly breakdown
                self._compute_hourly_breakdown(order_db, analytics_db, yesterday)
                
                # 3. Generate and store daily forecast
                self._generate_daily_forecast(analytics_db)
                
                # 4. Generate and store hourly forecast
                self._generate_hourly_forecast(analytics_db)
                
                analytics_db.commit()
                
                logger.info("=" * 60)
                logger.info("BATCH PROCESS COMPLETED SUCCESSFULLY")
                logger.info("=" * 60)
                
            except Exception as e:
                analytics_db.rollback()
                logger.error(f"Batch process error: {e}", exc_info=True)
                raise
            finally:
                order_db.close()
                analytics_db.close()
        
        finally:
            self.is_running = False
            batch_lock.release()
    
    def _compute_daily_revenue(self, order_db: Session, analytics_db: Session, target_date: date):
        """
        Compute daily revenue, order count, and average order value
        
        Args:
            order_db: Order database session (read-only)
            analytics_db: Analytics database session (read-write)
            target_date: Date to compute analytics for
        """
        logger.info(f"Computing daily revenue for {target_date}")
        
        # Query SERVED orders for the target date from order_db
        result = order_db.query(
            func.sum(Order.total_amount).label('total_revenue'),
            func.count(Order.id).label('order_count')
        ).filter(
            and_(
                Order.status == OrderStatus.SERVED,
                func.date(Order.created_at) == target_date
            )
        ).first()
        
        total_revenue = result.total_revenue or Decimal('0.00')
        order_count = result.order_count or 0
        average_order_value = (
            total_revenue / order_count if order_count > 0 else Decimal('0.00')
        )
        
        # UPSERT into daily_revenue_cache in analytics_db
        existing = analytics_db.query(DailyRevenueCache).filter(
            DailyRevenueCache.date == target_date
        ).first()
        
        if existing:
            existing.total_revenue = total_revenue
            existing.order_count = order_count
            existing.average_order_value = average_order_value
            logger.info(f"Updated daily revenue cache for {target_date}")
        else:
            cache_entry = DailyRevenueCache(
                date=target_date,
                total_revenue=total_revenue,
                order_count=order_count,
                average_order_value=average_order_value
            )
            analytics_db.add(cache_entry)
            logger.info(f"Inserted daily revenue cache for {target_date}")
        
        logger.info(f"  Revenue: ${total_revenue}, Orders: {order_count}, Avg: ${average_order_value}")
    
    def _compute_hourly_breakdown(self, order_db: Session, analytics_db: Session, target_date: date):
        """
        Compute hourly order counts
        
        Args:
            order_db: Order database session (read-only)
            analytics_db: Analytics database session (read-write)
            target_date: Date to compute analytics for
        """
        logger.info(f"Computing hourly breakdown for {target_date}")
        
        # Query order counts by hour from order_db
        results = order_db.query(
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count')
        ).filter(
            and_(
                Order.status == OrderStatus.SERVED,
                func.date(Order.created_at) == target_date
            )
        ).group_by('hour').all()
        
        # Create a dict for easy lookup
        hourly_data = {int(r.hour): r.order_count for r in results}
        
        # UPSERT for all 24 hours in analytics_db
        for hour in range(24):
            order_count = hourly_data.get(hour, 0)
            
            existing = analytics_db.query(HourlyOrderCache).filter(
                and_(
                    HourlyOrderCache.date == target_date,
                    HourlyOrderCache.hour == hour
                )
            ).first()
            
            if existing:
                existing.order_count = order_count
            else:
                cache_entry = HourlyOrderCache(
                    date=target_date,
                    hour=hour,
                    order_count=order_count
                )
                analytics_db.add(cache_entry)
        
        logger.info(f"  Stored hourly breakdown for {target_date}")
    
    def _generate_daily_forecast(self, analytics_db: Session):
        """
        Generate daily revenue forecast for the next 7 days
        
        Args:
            analytics_db: Analytics database session (read-write)
        """
        logger.info("Generating daily revenue forecast")
        
        # Get last `n` days of revenue data from analytics_db (configurable)
        cutoff_date = date.today() - timedelta(days=config.forecasting_history_days_daily)
        historical = analytics_db.query(
            DailyRevenueCache.date,
            DailyRevenueCache.total_revenue
        ).filter(
            DailyRevenueCache.date >= cutoff_date
        ).order_by(DailyRevenueCache.date).all()
        
        if not historical:
            logger.warning("No historical data available for forecasting")
            return
        
        # Prepare data for forecasting
        historical_data = [(r.date, r.total_revenue) for r in historical]
        
        # Generate forecast for next 7 days
        for days_ahead in range(1, 8):
            forecast_date = date.today() + timedelta(days=days_ahead)
            
            # Generate forecast that accounts for days ahead
            if days_ahead == 1:
                # Use ensemble for tomorrow
                forecast_value = self.forecasting_service.generate_daily_forecast(historical_data)
            else:
                # For future days, use the last forecast as additional data point
                # This creates a progressive forecast
                extended_data = historical_data.copy()
                for i in range(1, days_ahead):
                    prev_forecast_date = date.today() + timedelta(days=i)
                    prev_forecast = self.forecasting_service.generate_daily_forecast(extended_data)
                    extended_data.append((prev_forecast_date, prev_forecast))
                forecast_value = self.forecasting_service.generate_daily_forecast(extended_data)
            
            # Store forecast in analytics_db
            forecast_entry = ForecastHistory(
                forecast_type='daily_revenue',
                forecast_value=forecast_value,
                forecast_date=forecast_date
            )
            analytics_db.add(forecast_entry)
            
            logger.info(f"  Forecast for {forecast_date}: ${forecast_value}")
    
    def _generate_hourly_forecast(self, analytics_db: Session):
        """
        Generate hourly order count forecast for tomorrow
        
        Args:
            analytics_db: Analytics database session (read-write)
        """
        logger.info("Generating hourly forecast for tomorrow")
        
        # Get last `n` days of hourly data from analytics_db (configurable)
        cutoff_date = date.today() - timedelta(days=config.forecasting_history_days_hourly)
        historical = analytics_db.query(
            HourlyOrderCache.hour,
            HourlyOrderCache.order_count
        ).filter(
            HourlyOrderCache.date >= cutoff_date
        ).all()
        
        if not historical:
            logger.warning("No historical hourly data available for forecasting")
            return
        
        # Prepare data for forecasting
        hourly_data = [(r.hour, r.order_count) for r in historical]
        
        # Generate hourly forecasts
        forecasts = self.forecasting_service.generate_hourly_forecast(hourly_data)
        
        tomorrow = date.today() + timedelta(days=1)
        
        for hour, forecast_value in forecasts:
            forecast_entry = ForecastHistory(
                forecast_type=f'hourly_{hour:02d}',
                forecast_value=forecast_value,
                forecast_date=tomorrow
            )
            analytics_db.add(forecast_entry)
        
        logger.info(f"  Stored 24-hour forecast for {tomorrow}")


# Global batch processor instance
batch_processor = BatchProcessor()
