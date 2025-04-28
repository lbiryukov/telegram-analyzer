import os
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from backend.telegram_analyzer import Base, TelegramMessage, TelegramAnalyzer
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_database.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestDatabase')

class DatabaseTester:
    def __init__(self):
        self.test_db_path = 'test_telegram_messages.db'
        self.engine = create_engine(f'sqlite:///{self.test_db_path}')
        self.Session = sessionmaker(bind=self.engine)
        
    def setup_test_database(self):
        """Drop and recreate the test database."""
        logger.info("Setting up test database...")
        
        # Drop the test database if it exists
        if os.path.exists(self.test_db_path):
            logger.info(f"Removing existing test database: {self.test_db_path}")
            os.remove(self.test_db_path)
        
        # Create new database with schema
        logger.info("Creating new test database with schema")
        Base.metadata.create_all(self.engine)
        
        # Verify the database was created
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        logger.info(f"Created tables: {tables}")
        
        return len(tables) > 0
    
    def get_db_stats(self):
        """Get current database statistics."""
        session = self.Session()
        try:
            # Get total message count
            total_messages = session.query(TelegramMessage).count()
            
            # Get message count per chat
            chat_stats = session.query(
                TelegramMessage.chat_title,
                func.count(TelegramMessage.id).label('message_count')
            ).group_by(TelegramMessage.chat_title).all()
            
            # Get date range
            min_date = session.query(func.min(TelegramMessage.date)).scalar()
            max_date = session.query(func.max(TelegramMessage.date)).scalar()
            
            logger.info("\nDatabase Statistics:")
            logger.info(f"Total messages: {total_messages}")
            logger.info("\nMessages per chat:")
            for chat_title, count in chat_stats:
                logger.info(f"{chat_title}: {count} messages")
            logger.info(f"\nDate range: {min_date} to {max_date}")
            
            return total_messages, chat_stats
            
        finally:
            session.close()
    
    async def test_message_fetching(self):
        """Test message fetching with different scenarios."""
        try:
            # Create analyzer with test database
            analyzer = TelegramAnalyzer(db_path=self.test_db_path)
            
            # Test 1: Fetch messages from The Bell for 1 day
            logger.info("\nTest 1: Fetching messages from The Bell for 1 day")
            result = await analyzer.fetch_messages(
                chat_urls=["https://t.me/thebell_io"],
                telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                days_back=1
            )
            logger.info(f"Test 1 result: {result}")
            total_messages, chat_stats = self.get_db_stats()
            assert total_messages > 0, "No messages were fetched in Test 1"
            
            # Test 2: Fetch messages from The Bell for 2 days
            logger.info("\nTest 2: Fetching messages from The Bell for 2 days")
            result = await analyzer.fetch_messages(
                chat_urls=["https://t.me/thebell_io"],
                telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                days_back=2
            )
            logger.info(f"Test 2 result: {result}")
            total_messages, chat_stats = self.get_db_stats()
            assert total_messages > 0, "No messages were fetched in Test 2"
            
            # Test 3: Fetch messages from multiple channels for 3 days
            logger.info("\nTest 3: Fetching messages from multiple channels for 3 days")
            result = await analyzer.fetch_messages(
                chat_urls=["https://t.me/bbcrussian", "https://t.me/meduzalive"],
                telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                days_back=3
            )
            logger.info(f"Test 3 result: {result}")
            total_messages, chat_stats = self.get_db_stats()
            assert total_messages > 0, "No messages were fetched in Test 3"
            
            return True
            
        except Exception as e:
            logger.error(f"Error during message fetching tests: {str(e)}")
            return False
    
    def cleanup(self):
        """Clean up test database."""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
            logger.info("Test database removed")

async def run_tests():
    """Run all database tests."""
    tester = DatabaseTester()
    try:
        # Setup test database
        if not tester.setup_test_database():
            logger.error("Failed to setup test database")
            return False
        
        # Run message fetching tests
        test_result = await tester.test_message_fetching()
        if not test_result:
            logger.error("Message fetching tests failed")
            return False
        
        logger.info("All tests completed successfully")
        return True
        
    except AssertionError as e:
        logger.error(f"Test assertion failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    asyncio.run(run_tests()) 