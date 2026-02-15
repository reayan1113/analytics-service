from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel, Field

# Define nested config models
class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8087

class DatabaseConfig(BaseModel):
    host: str = "localhost"
    port: int = 3306
    username: str = "root"
    password: str = ""
    database: str = "db"

class ForecastingConfig(BaseModel):
    moving_average_window: int = 7
    enable_linear_regression: bool = True
    enable_ensemble_method: bool = True
    exponential_smoothing_alpha: float = 0.3
    trend_smoothing_beta: float = 0.1
    seasonal_periods: int = 7
    polynomial_degree: int = 2
    outlier_detection_enabled: bool = True
    history_days_daily: int = 30
    history_days_hourly: int = 7

class SchedulerConfig(BaseModel):
    enabled: bool = True
    run_time: str = "00:00"

class Settings(BaseSettings):
    """
    Configuration management using Pydantic Settings.
    Reads from environment variables and .env file.
    """
    server: ServerConfig = ServerConfig()
    order_database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    analytics_database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    forecasting: ForecastingConfig = ForecastingConfig()
    scheduler: SchedulerConfig = SchedulerConfig()

    model_config = SettingsConfigDict(
        env_nested_delimiter='__',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Backward compatibility properties to match the old Config interface
    @property
    def server_host(self) -> str:
        return self.server.host
    
    @property
    def server_port(self) -> int:
        return self.server.port
    
    # Order Database (read-only)
    @property
    def order_db_host(self) -> str:
        return self.order_database.host
    
    @property
    def order_db_port(self) -> int:
        return self.order_database.port
    
    @property
    def order_db_username(self) -> str:
        return self.order_database.username
    
    @property
    def order_db_password(self) -> str:
        return self.order_database.password
    
    @property
    def order_db_database(self) -> str:
        return self.order_database.database
    
    # Analytics Database (read-write)
    @property
    def analytics_db_host(self) -> str:
        return self.analytics_database.host
    
    @property
    def analytics_db_port(self) -> int:
        return self.analytics_database.port
    
    @property
    def analytics_db_username(self) -> str:
        return self.analytics_database.username
    
    @property
    def analytics_db_password(self) -> str:
        return self.analytics_database.password
    
    @property
    def analytics_db_database(self) -> str:
        return self.analytics_database.database
    
    @property
    def forecasting_window(self) -> int:
        return self.forecasting.moving_average_window

    @property
    def forecasting_history_days_daily(self) -> int:
        return self.forecasting.history_days_daily

    @property
    def forecasting_history_days_hourly(self) -> int:
        return self.forecasting.history_days_hourly
    
    @property
    def enable_linear_regression(self) -> bool:
        return self.forecasting.enable_linear_regression
    
    @property
    def enable_ensemble_method(self) -> bool:
        return self.forecasting.enable_ensemble_method
    
    @property
    def exponential_smoothing_alpha(self) -> float:
        return self.forecasting.exponential_smoothing_alpha
    
    @property
    def trend_smoothing_beta(self) -> float:
        return self.forecasting.trend_smoothing_beta
    
    @property
    def seasonal_periods(self) -> int:
        return self.forecasting.seasonal_periods
    
    @property
    def polynomial_degree(self) -> int:
        return self.forecasting.polynomial_degree
    
    @property
    def outlier_detection_enabled(self) -> bool:
        return self.forecasting.outlier_detection_enabled
    
    @property
    def scheduler_enabled(self) -> bool:
        return self.scheduler.enabled
    
    @property
    def scheduler_run_time(self) -> str:
        return self.scheduler.run_time

# Global config instance
config = Settings()
