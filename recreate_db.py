import os
from backend.telegram_analyzer import Base, TelegramAnalyzer
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recreate_db.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('RecreateDB')

def recreate_database():
    """Recreate the database with the new schema."""
    try:
        # Delete existing database file
        if os.path.exists('telegram_messages.db'):
            logger.info("Removing existing database file")
            os.remove('telegram_messages.db')
        
        # Create new database with updated schema
        logger.info("Creating new database with updated schema")
        analyzer = TelegramAnalyzer()
        
        logger.info("Database recreation completed successfully")
    except Exception as e:
        logger.error(f"Error recreating database: {str(e)}")

if __name__ == "__main__":
    recreate_database() 