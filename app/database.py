import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from urllib.parse import quote_plus
import pymysql

from app.config import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Two separate base classes for the two databases
OrderBase = declarative_base()
AnalyticsBase = declarative_base()

# Database engines and sessions
order_engine = None
analytics_engine = None
OrderSessionLocal = None
AnalyticsSessionLocal = None


def create_analytics_database_if_not_exists():
    """Create analytics database if it doesn't exist"""
    try:
        # URL encode username and password
        username = quote_plus(config.analytics_db_username)
        password = quote_plus(config.analytics_db_password)

        print(username, password)
        
        # Connect without specifying database - with SSL for Azure
        connection_url = f"mysql+pymysql://{username}:{password}@{config.analytics_db_host}:{config.analytics_db_port}/?ssl_ca=&ssl_verify_cert=false"
        temp_engine = create_engine(connection_url)
        
        with temp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{config.analytics_db_database}'")
            )
            exists = result.fetchone() is not None
            
            if not exists:
                conn.execute(text(f"CREATE DATABASE {config.analytics_db_database}"))
                conn.commit()
                logger.info(f"Analytics database '{config.analytics_db_database}' created successfully")
            else:
                logger.info(f"Analytics database '{config.analytics_db_database}' already exists")
        
        temp_engine.dispose()
    except Exception as e:
        logger.error(f"Error creating analytics database: {e}")
        raise


def init_database():
    """Initialize database connections for both order and analytics databases"""
    global order_engine, analytics_engine, OrderSessionLocal, AnalyticsSessionLocal
    
    # Create analytics database if it doesn't exist
    create_analytics_database_if_not_exists()
    
    # URL encode credentials
    order_username = quote_plus(config.order_db_username)
    order_password = quote_plus(config.order_db_password)
    analytics_username = quote_plus(config.analytics_db_username)
    analytics_password = quote_plus(config.analytics_db_password)
    
    # Create order database engine (read-only access to existing database) with SSL
    order_database_url = f"mysql+pymysql://{order_username}:{order_password}@{config.order_db_host}:{config.order_db_port}/{config.order_db_database}?ssl_ca=&ssl_verify_cert=false"
    
    order_engine = create_engine(
        order_database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    # Create analytics database engine (read-write access) with SSL
    analytics_database_url = f"mysql+pymysql://{analytics_username}:{analytics_password}@{config.analytics_db_host}:{config.analytics_db_port}/{config.analytics_db_database}?ssl_ca=&ssl_verify_cert=false"
    
    analytics_engine = create_engine(
        analytics_database_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False
    )
    
    # Update global session makers
    OrderSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=order_engine)
    AnalyticsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=analytics_engine)
    
    logger.info(f"Order session created: {OrderSessionLocal is not None}")
    logger.info(f"Analytics session created: {AnalyticsSessionLocal is not None}")
    
    # Import models to register them
    from app.models import order, analytics
    
    # Create analytics tables only (order tables already exist in order_db)
    AnalyticsBase.metadata.create_all(bind=analytics_engine)
    logger.info("Analytics tables created successfully in analytics_db")
    logger.info(f"Connected to order_db at {config.order_db_host}:{config.order_db_port}/{config.order_db_database}")
    logger.info(f"Connected to analytics_db at {config.analytics_db_host}:{config.analytics_db_port}/{config.analytics_db_database}")
    
    return order_engine, analytics_engine


@contextmanager
def get_order_db():
    """Get order database session context manager"""
    db = OrderSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_analytics_db():
    """Get analytics database session context manager"""
    db = AnalyticsSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_order_db_session():
    """Get order database session for dependency injection"""
    db = OrderSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_analytics_db_session():
    """Get analytics database session for dependency injection"""
    db = AnalyticsSessionLocal()
    try:
        yield db
    finally:
        db.close()
