from sqlalchemy import create_engine, inspect, func
from sqlalchemy.orm import sessionmaker
from backend.telegram_analyzer import TelegramMessage
import logging
from collections import defaultdict
from typing import List
from sqlalchemy import and_, or_
from datetime import datetime, timedelta

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

def test_message_retrieval(chat_id: str, keywords: List[str], start_date: datetime, end_date: datetime):
    """Test message retrieval with specific parameters."""
    try:
        # Create engine and session
        engine = create_engine('sqlite:///telegram_messages.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Prepare search conditions
        keyword_conditions = [TelegramMessage.text.ilike(f'%{keyword}%') for keyword in keywords]
        
        # Get messages containing keywords
        keyword_messages = session.query(TelegramMessage).filter(
            and_(
                TelegramMessage.chat_id == chat_id,
                TelegramMessage.date >= start_date,
                TelegramMessage.date <= end_date,
                or_(*keyword_conditions)
            )
        ).order_by(TelegramMessage.date).all()
        
        logger.info(f"\nFound {len(keyword_messages)} messages matching keywords:")
        for msg in keyword_messages:
            logger.info(f"""
            Date: {msg.date}
            Sender: {msg.sender}
            Text: {msg.text[:100]}{'...' if len(msg.text) > 100 else ''}
            """)
            
    except Exception as e:
        logger.error(f"Error testing message retrieval: {str(e)}")
    finally:
        session.close()

def search_messages(chat_id: str, keyword: str):
    """Search for messages containing specific keyword in a chat."""
    try:
        # Create engine and session
        engine = create_engine('sqlite:///telegram_messages.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Search for messages
        messages = session.query(TelegramMessage).filter(
            and_(
                TelegramMessage.chat_id == chat_id,
                TelegramMessage.text.ilike(f'%{keyword}%')
            )
        ).order_by(TelegramMessage.date.desc()).all()
        
        logger.info(f"\nSearching for messages containing '{keyword}' in chat {chat_id}:")
        if messages:
            logger.info(f"Found {len(messages)} messages:")
            for msg in messages:
                logger.info(f"""
                Date: {msg.date}
                Sender: {msg.sender}
                Text: {msg.text}
                """)
        else:
            logger.info("No messages found")
            
    except Exception as e:
        logger.error(f"Error searching messages: {str(e)}")
    finally:
        session.close()

def list_chats():
    """List all chats and their IDs from the database."""
    try:
        # Create engine and session
        engine = create_engine('sqlite:///telegram_messages.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get unique chats
        chats = session.query(
            TelegramMessage.chat_id,
            TelegramMessage.chat_title,
            func.count(TelegramMessage.id).label('message_count')
        ).group_by(
            TelegramMessage.chat_id,
            TelegramMessage.chat_title
        ).order_by(func.count(TelegramMessage.id).desc()).all()
        
        logger.info("\nAvailable chats in database:")
        for chat_id, chat_title, count in chats:
            logger.info(f"Chat: {chat_title}")
            logger.info(f"ID: {chat_id}")
            logger.info(f"Messages: {count}")
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"Error listing chats: {str(e)}")
    finally:
        session.close()

def get_recent_messages(chat_id: str, limit: int = 5):
    """Get recent messages from a specific chat with dates and times."""
    try:
        # Create engine and session
        engine = create_engine('sqlite:///telegram_messages.db')
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get recent messages
        messages = session.query(TelegramMessage).filter(
            TelegramMessage.chat_id == chat_id
        ).order_by(TelegramMessage.date.desc()).limit(limit).all()
        
        logger.info(f"\nRecent messages from chat {chat_id}:")
        for msg in messages:
            logger.info(f"""
            Date: {msg.date.strftime('%Y-%m-%d %H:%M:%S')}
            Sender: {msg.sender}
            Text: {msg.text[:200]}{'...' if len(msg.text) > 200 else ''}
            """)
            
    except Exception as e:
        logger.error(f"Error retrieving messages: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    # Search for messages about croissants in ВАКЕ chat
    search_messages(
        chat_id="1674641002",  # ВАКЕ | Тбилиси chat ID
        keyword="круассан"
    )
    # Check database contents
    check_database() 