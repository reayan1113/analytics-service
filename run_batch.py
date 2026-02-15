"""
Manual batch execution script
Run this to manually trigger the midnight batch process
"""
import sys
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import config
from app.database import init_database
from app.scheduler.batch_processor import BatchProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Run the batch process manually"""
    logger.info("=" * 60)
    logger.info("MANUAL BATCH EXECUTION")
    logger.info("=" * 60)
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Create batch processor
        processor = BatchProcessor()
        
        # Run batch job
        logger.info("Executing batch job...")
        processor.run_batch_job()
        
        logger.info("=" * 60)
        logger.info("MANUAL BATCH EXECUTION COMPLETED")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Batch execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
