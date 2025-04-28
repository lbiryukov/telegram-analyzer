from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from backend.telegram_analyzer import TelegramMessage
import logging
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_db.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestDB')

def check_database():
    """Check the contents of the database and find duplicates."""
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
        
        # Get all messages
        messages = session.query(TelegramMessage).all()
        
        # Count messages per chat
        chat_stats = session.query(
            TelegramMessage.chat_title,
            func.count(TelegramMessage.id).label('message_count')
        ).group_by(TelegramMessage.chat_title).all()
        
        logger.info("\nMessage count per chat:")
        for chat_title, count in chat_stats:
            logger.info(f"{chat_title}: {count} messages")
        
        # Check for duplicates using chat_id and message_id
        message_keys = defaultdict(list)
        for msg in messages:
            key = (msg.chat_id, msg.message_id)
            message_keys[key].append(msg)
        
        # Find duplicates
        duplicates = {key: msgs for key, msgs in message_keys.items() if len(msgs) > 1}
        
        if duplicates:
            logger.info("\nFound duplicate messages:")
            for (chat_id, message_id), msgs in duplicates.items():
                logger.info(f"\nDuplicate messages for chat_id={chat_id}, message_id={message_id}:")
                for msg in msgs:
                    logger.info(f"""
                    ID: {msg.id}
                    Date: {msg.date}
                    Sender: {msg.sender}
                    Message: {msg.text[:100]}{'...' if len(msg.text) > 100 else ''}
                    """)
        else:
            logger.info("\nNo duplicate messages found")
            
    except Exception as e:
        logger.error(f"Error checking database: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    check_database() 