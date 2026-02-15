"""
FastAPI main application
Analytics Microservice
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.config import config
from app.database import init_database
from app.routers import analytics
from app.scheduler.batch_processor import batch_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # Startup
    logger.info("=" * 60)
    logger.info("ANALYTICS SERVICE STARTING")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        init_database()
        logger.info("Database initialized successfully")
        
        # Start scheduler
        logger.info("Starting batch scheduler...")
        batch_processor.start()
        logger.info("Batch scheduler started successfully")
        
        logger.info("=" * 60)
        logger.info("ANALYTICS SERVICE READY")
        logger.info(f"Server: http://{config.server_host}:{config.server_port}")
        logger.info("=" * 60)
        
        yield
        
    finally:
        # Shutdown
        logger.info("=" * 60)
        logger.info("ANALYTICS SERVICE SHUTTING DOWN")
        logger.info("=" * 60)
        
        # Stop scheduler
        logger.info("Stopping batch scheduler...")
        batch_processor.stop()
        logger.info("Batch scheduler stopped")
        
        logger.info("Analytics service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Analytics Service",
    description="Production-ready analytics microservice with scheduled batch processing",
    version="1.0.0",
    lifespan=lifespan
)

# Include routers
app.include_router(analytics.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "analytics-service",
        "version": "1.0.0",
        "status": "running",
        "scheduler_running": batch_processor.scheduler is not None,
        "batch_in_progress": batch_processor.is_running
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "scheduler": "active" if batch_processor.scheduler else "inactive"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=config.server_host,
        port=config.server_port,
        reload=False,
        log_level="info"
    )
