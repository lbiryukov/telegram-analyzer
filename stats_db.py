from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from backend.telegram_analyzer import TelegramMessage
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stats_db.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('StatsDB')

def get_database_stats():
    """Get comprehensive statistics about the database."""
    try:
        # Create engine and session
        engine = create_engine('sqlite:///telegram_messages.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get table information
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Found tables: {tables}")
        
        if 'telegram_messages' not in tables:
            logger.error("telegram_messages table not found")
            return
        
        # Get total number of different chats
        chat_count = session.query(TelegramMessage.chat_id).distinct().count()
        logger.info(f"\nTotal number of different chats: {chat_count}")
        
        # Get total number of messages
        total_messages = session.query(TelegramMessage).count()
        logger.info(f"Total number of messages: {total_messages}")
        
        # Get oldest and newest message dates
        oldest_date = session.query(func.min(TelegramMessage.date)).scalar()
        newest_date = session.query(func.max(TelegramMessage.date)).scalar()
        logger.info(f"Date range: {oldest_date} to {newest_date}")
        
        # Get all chats with their statistics
        chat_stats = session.query(
            TelegramMessage.chat_id,
            TelegramMessage.chat_title,
            func.count(TelegramMessage.id).label('message_count'),
            func.min(TelegramMessage.date).label('oldest_date'),
            func.max(TelegramMessage.date).label('newest_date')
        ).group_by(TelegramMessage.chat_id, TelegramMessage.chat_title)\
         .order_by(func.count(TelegramMessage.id).desc()).all()
        
        logger.info("\nTop 10 chats by message count:")
        for i, (chat_id, chat_title, count, oldest, newest) in enumerate(chat_stats, 1):
            logger.info(f"""
            {i}. Chat: {chat_title}
               ID: {chat_id}
               Messages: {count}
               Date range: {oldest} to {newest}
            """)
            
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    get_database_stats() 