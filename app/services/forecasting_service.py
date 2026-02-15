"""Forecasting service for statistical predictions with improved methods"""
import logging
from typing import List, Tuple, Optional, Dict
from datetime import date, timedelta
from decimal import Decimal
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from statistics import median, stdev

from app.config import config

logger = logging.getLogger(__name__)


class ForecastingService:
    """Service for generating statistical forecasts with improved statistical methods"""
    
    def __init__(self):
        self.moving_average_window = config.forecasting_window
        self.enable_linear_regression = config.enable_linear_regression
        self.enable_ensemble = config.enable_ensemble_method
        self.alpha = config.exponential_smoothing_alpha
        self.beta = config.trend_smoothing_beta
        self.seasonal_periods = config.seasonal_periods
        self.polynomial_degree = config.polynomial_degree
        self.outlier_detection = config.outlier_detection_enabled
    
    def _remove_outliers(self, data: List[float]) -> List[float]:
        """
        Remove statistical outliers using IQR method
        
        Args:
            data: List of numeric values
            
        Returns:
            Cleaned data without outliers
        """
        if not self.outlier_detection or len(data) < 4:
            return data
        
        try:
            q1 = np.percentile(data, 25)
            q3 = np.percentile(data, 75)
            iqr = q3 - q1
            
            lower_bound = q1 - (1.5 * iqr)
            upper_bound = q3 + (1.5 * iqr)
            
            # Replace outliers with median instead of removing
            med = np.median(data)
            cleaned = [x if lower_bound <= x <= upper_bound else med for x in data]
            
            return cleaned
        except Exception as e:
            logger.warning(f"Outlier removal failed: {e}, returning original data")
            return data
    
    def exponential_smoothing_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]]
    ) -> Decimal:
        """
        Double exponential smoothing (Holt's method) - handles trend
        
        Args:
            historical_data: List of (date, value) tuples
            
        Returns:
            Forecasted value
        """
        if not historical_data:
            return Decimal('0.00')
        
        try:
            # Sort by date
            sorted_data = sorted(historical_data, key=lambda x: x[0])
            values = [float(value) for _, value in sorted_data]
            
            # Remove outliers
            values = self._remove_outliers(values)
            
            if len(values) < 2:
                return Decimal(str(round(values[0] if values else 0, 2)))
            
            # Initialize level and trend
            level = values[0]
            trend = values[1] - values[0] if len(values) > 1 else 0
            
            # Apply double exponential smoothing
            for value in values[1:]:
                last_level = level
                level = self.alpha * value + (1 - self.alpha) * (level + trend)
                trend = self.beta * (level - last_level) + (1 - self.beta) * trend
            
            # Forecast next value (level + trend)
            next_forecast = max(0, level + trend)
            
            return Decimal(str(round(next_forecast, 2)))
        except Exception as e:
            logger.error(f"Exponential smoothing forecast error: {e}")
            return Decimal('0.00')
    
    def weighted_moving_average_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]]
    ) -> Decimal:
        """
        Weighted moving average (exponentially more weight on recent data)
        
        Args:
            historical_data: List of (date, value) tuples
            
        Returns:
            Forecasted value
        """
        if not historical_data:
            return Decimal('0.00')
        
        try:
            # Sort by date
            sorted_data = sorted(historical_data, key=lambda x: x[0])
            
            # Get last N values
            window_data = sorted_data[-self.moving_average_window:]
            
            if not window_data:
                return Decimal('0.00')
            
            values = [float(value) for _, value in window_data]
            
            # Remove outliers
            values = self._remove_outliers(values)
            
            if not values:
                return Decimal('0.00')
            
            # Create exponential weights (more weight to recent)
            n = len(values)
            weights = np.exp(np.linspace(0, 1, n))
            weights = weights / weights.sum()
            
            # Calculate weighted average
            weighted_avg = np.dot(values, weights)
            
            return Decimal(str(round(weighted_avg, 2)))
        except Exception as e:
            logger.error(f"Weighted moving average error: {e}")
            return Decimal('0.00')
    
    def polynomial_regression_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]], 
        days_ahead: int = 1,
        degree: int = None
    ) -> Decimal:
        """
        Polynomial regression for non-linear trends
        
        Args:
            historical_data: List of (date, value) tuples
            days_ahead: Number of days to forecast ahead
            degree: Polynomial degree (None uses config value)
            
        Returns:
            Forecasted value
        """
        if degree is None:
            degree = self.polynomial_degree
            
        if not historical_data or len(historical_data) < degree + 1:
            return Decimal('0.00')
        
        try:
            # Sort by date
            sorted_data = sorted(historical_data, key=lambda x: x[0])
            
            # Prepare data
            first_date = sorted_data[0][0]
            X = np.array([[(d - first_date).days] for d, _ in sorted_data])
            y = np.array([float(value) for _, value in sorted_data])
            
            # Remove outliers
            y = self._remove_outliers(list(y))
            y = np.array(y)
            
            # Create polynomial features
            poly_features = PolynomialFeatures(degree=degree)
            X_poly = poly_features.fit_transform(X)
            
            # Fit polynomial regression
            model = LinearRegression()
            model.fit(X_poly, y)
            
            # Predict for next day(s)
            last_date = sorted_data[-1][0]
            next_day = (last_date + timedelta(days=days_ahead) - first_date).days
            X_next = poly_features.transform([[next_day]])
            prediction = model.predict(X_next)[0]
            
            # Ensure non-negative prediction
            prediction = max(0, prediction)
            
            return Decimal(str(round(prediction, 2)))
        
        except Exception as e:
            logger.error(f"Polynomial regression forecast error: {e}")
            return Decimal('0.00')
    
    def linear_regression_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]], 
        days_ahead: int = 1
    ) -> Decimal:
        """
        Linear regression forecast with outlier handling
        
        Args:
            historical_data: List of (date, value) tuples
            days_ahead: Number of days to forecast ahead
            
        Returns:
            Forecasted value
        """
        if not historical_data or len(historical_data) < 2:
            return Decimal('0.00')
        
        try:
            # Sort by date
            sorted_data = sorted(historical_data, key=lambda x: x[0])
            
            # Prepare data for regression
            first_date = sorted_data[0][0]
            X = np.array([[(d - first_date).days] for d, _ in sorted_data])
            y = np.array([float(value) for _, value in sorted_data])
            
            # Remove outliers
            y = self._remove_outliers(list(y))
            y = np.array(y)
            
            # Fit linear regression model
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict for next day(s)
            last_date = sorted_data[-1][0]
            next_day = (last_date + timedelta(days=days_ahead) - first_date).days
            prediction = model.predict([[next_day]])[0]
            
            # Ensure non-negative prediction
            prediction = max(0, prediction)
            
            return Decimal(str(round(prediction, 2)))
        
        except Exception as e:
            logger.error(f"Linear regression forecast error: {e}")
            return Decimal('0.00')
    
    def ensemble_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]]
    ) -> Decimal:
        """
        Ensemble method combining multiple forecasting techniques
        Uses weighted average of different methods for more robust prediction
        
        Args:
            historical_data: List of (date, revenue) tuples
            
        Returns:
            Combined forecasted value
        """
        if not historical_data:
            return Decimal('0.00')
        
        try:
            forecasts = []
            weights = []
            
            # Exponential smoothing (30% weight) - good for recent trends
            exp_forecast = self.exponential_smoothing_forecast(historical_data)
            if exp_forecast > 0:
                forecasts.append(float(exp_forecast))
                weights.append(0.30)
            
            # Weighted moving average (25% weight) - stable baseline
            wma_forecast = self.weighted_moving_average_forecast(historical_data)
            if wma_forecast > 0:
                forecasts.append(float(wma_forecast))
                weights.append(0.25)
            
            # Linear regression (25% weight) - captures linear trends
            if len(historical_data) >= 3:
                lr_forecast = self.linear_regression_forecast(historical_data)
                if lr_forecast > 0:
                    forecasts.append(float(lr_forecast))
                    weights.append(0.25)
            
            # Polynomial regression (20% weight) - captures non-linear patterns
            if len(historical_data) >= 5:
                poly_forecast = self.polynomial_regression_forecast(historical_data)
                if poly_forecast > 0:
                    forecasts.append(float(poly_forecast))
                    weights.append(0.20)
            
            if not forecasts:
                return Decimal('0.00')
            
            # Normalize weights
            total_weight = sum(weights)
            normalized_weights = [w / total_weight for w in weights]
            
            # Calculate weighted average
            ensemble_result = sum(f * w for f, w in zip(forecasts, normalized_weights))
            
            return Decimal(str(round(ensemble_result, 2)))
        
        except Exception as e:
            logger.error(f"Ensemble forecast error: {e}")
            # Fallback to exponential smoothing
            return self.exponential_smoothing_forecast(historical_data)
    
    def generate_daily_forecast(
        self, 
        historical_data: List[Tuple[date, Decimal]]
    ) -> Decimal:
        """
        Generate daily revenue forecast using ensemble or single method
        
        Args:
            historical_data: List of (date, revenue) tuples
            
        Returns:
            Forecasted revenue for next day
        """
        if not historical_data:
            return Decimal('0.00')
        
        # Use ensemble method if enabled, otherwise exponential smoothing
        if self.enable_ensemble:
            return self.ensemble_forecast(historical_data)
        else:
            return self.exponential_smoothing_forecast(historical_data)
    
    def generate_hourly_forecast(
        self, 
        hourly_data: List[Tuple[int, int]]
    ) -> List[Tuple[int, Decimal]]:
        """
        Generate hourly order count forecast with seasonal patterns
        
        Args:
            hourly_data: List of (hour, order_count) tuples from recent days
            
        Returns:
            List of (hour, forecasted_count) tuples for each hour (0-23)
        """
        if not hourly_data:
            return [(hour, Decimal('0.00')) for hour in range(24)]
        
        try:
            # Group by hour
            hour_groups: Dict[int, List[int]] = {}
            for hour, count in hourly_data:
                if hour not in hour_groups:
                    hour_groups[hour] = []
                hour_groups[hour].append(count)
            
            forecasts = []
            for hour in range(24):
                if hour in hour_groups and hour_groups[hour]:
                    values = hour_groups[hour]
                    
                    # Remove outliers
                    cleaned_values = self._remove_outliers([float(v) for v in values])
                    
                    if cleaned_values:
                        # Use exponential weighted average for hourly forecast
                        n = len(cleaned_values)
                        if n > 1:
                            weights = np.exp(np.linspace(0, 1, n))
                            weights = weights / weights.sum()
                            avg_count = np.dot(cleaned_values, weights)
                        else:
                            avg_count = cleaned_values[0]
                        
                        forecasts.append((hour, Decimal(str(round(avg_count, 2)))))
                    else:
                        forecasts.append((hour, Decimal('0.00')))
                else:
                    # No data for this hour, use interpolation from neighbors
                    forecasts.append((hour, Decimal('0.00')))
            
            # Fill missing hours with interpolated values
            forecasts = self._interpolate_missing_hours(forecasts)
            
            return forecasts
        
        except Exception as e:
            logger.error(f"Hourly forecast error: {e}")
            return [(hour, Decimal('0.00')) for hour in range(24)]
    
    def _interpolate_missing_hours(
        self, 
        forecasts: List[Tuple[int, Decimal]]
    ) -> List[Tuple[int, Decimal]]:
        """
        Interpolate values for hours with zero forecast using neighbors
        
        Args:
            forecasts: List of (hour, forecast) tuples
            
        Returns:
            Forecasts with interpolated values for missing hours
        """
        result = []
        for i, (hour, value) in enumerate(forecasts):
            if value == Decimal('0.00') and i > 0 and i < len(forecasts) - 1:
                # Find nearest non-zero neighbors
                prev_val = forecasts[i-1][1]
                next_val = forecasts[i+1][1]
                
                if prev_val > 0 or next_val > 0:
                    # Linear interpolation
                    interpolated = (float(prev_val) + float(next_val)) / 2
                    result.append((hour, Decimal(str(round(interpolated, 2)))))
                else:
                    result.append((hour, value))
            else:
                result.append((hour, value))
        
        return result
