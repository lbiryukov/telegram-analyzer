from telethon import TelegramClient
from telethon.sessions import StringSession
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, inspect, UniqueConstraint, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime, timedelta
import re
from typing import List, Dict, Any
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_analyzer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TelegramAnalyzer')

Base = declarative_base()

class TelegramMessage(Base):
    __tablename__ = 'telegram_messages'
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(String)
    message_id = Column(Integer)
    date = Column(DateTime)
    text = Column(Text)
    sender = Column(String)
    chat_title = Column(String)
    
    # Add unique constraint on chat_id and message_id
    __table_args__ = (
        UniqueConstraint('chat_id', 'message_id', name='uix_chat_message'),
    )

class TelegramAnalyzer:
    def __init__(self, db_path='telegram_messages.db'):
        logger.info("Initializing TelegramAnalyzer")
        self.db_engine = create_engine(f'sqlite:///{db_path}')
        
        # Check if tables exist before creating them
        inspector = inspect(self.db_engine)
        if not inspector.has_table('telegram_messages'):
            logger.info("Creating telegram_messages table")
            Base.metadata.create_all(self.db_engine)
        else:
            logger.info("telegram_messages table already exists")
            
        self.Session = sessionmaker(bind=self.db_engine)

    async def _fetch_telegram_messages(self, client: TelegramClient, chat_url: str, 
                                     start_date: datetime = None, end_date: datetime = None) -> List[Dict[str, Any]]:
        """Fetch messages from a Telegram chat."""
        try:
            logger.info(f"Fetching messages from {chat_url}")
            # Extract chat ID from URL
            chat_name = re.search(r't\.me/([^/]+)', chat_url).group(1)
            logger.info(f"Extracted chat name: {chat_name}")
            
            # Get chat entity
            chat = await client.get_entity(chat_name)
            logger.info(f"Found chat: {chat.title} (ID: {chat.id})")
            
            # Get numeric chat ID
            chat_id = str(chat.id)
            
            # Get message IDs for our date range
            start_message = await client.get_messages(chat, offset_date=start_date, limit=1)
            end_message = await client.get_messages(chat, offset_date=end_date, limit=1)
            
            if not start_message or not end_message:
                logger.info("No messages found in date range")
                return []
                
            min_id = start_message[0].id
            max_id = end_message[0].id
            
            logger.info(f"Fetching messages with IDs between {min_id} and {max_id}")
            
            # Fetch messages with ID filtering
            messages = []
            message_count = 0
            total_messages = 0
            
            # Fetch messages in chunks
            current_id = max_id
            while current_id >= min_id:
                chunk = await client.get_messages(
                    chat,
                    limit=100,  # Fetch in smaller chunks
                    min_id=min_id,
                    max_id=current_id
                )
                
                if not chunk:
                    break
                
                logger.info(f"Fetched chunk of {len(chunk)} messages")
                total_messages += len(chunk)
                
                for message in chunk:
                    if not message.text:
                        continue
                        
                    messages.append({
                        'chat_id': chat_id,
                        'message_id': message.id,
                        'date': message.date.replace(tzinfo=None),
                        'text': message.text,
                        'sender': str(message.sender_id),
                        'chat_title': chat.title
                    })
                    message_count += 1
                
                # Update current_id for next chunk
                current_id = chunk[-1].id - 1
            
            logger.info(f"Fetched {message_count} messages from {chat.title} (total messages in range: {total_messages})")
            return messages
        except Exception as e:
            logger.error(f"Error fetching messages from {chat_url}: {str(e)}")
            return []

    def _store_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Store messages in SQLite database. Returns number of new messages stored."""
        if not messages:
            logger.warning("No messages to store")
            return 0
            
        logger.info(f"Storing {len(messages)} messages")
        session = self.Session()
        
        try:
            new_messages = 0
            for msg in messages:
                # Check if message already exists
                existing = session.query(TelegramMessage).filter_by(
                    chat_id=msg['chat_id'],
                    message_id=msg['message_id']
                ).first()
                
                if not existing:
                    db_message = TelegramMessage(
                        chat_id=msg['chat_id'],
                        message_id=msg['message_id'],
                        date=msg['date'],
                        text=msg['text'],
                        sender=msg['sender'],
                        chat_title=msg['chat_title']
                    )
                    session.add(db_message)
                    new_messages += 1
            
            session.commit()
            logger.info(f"Successfully stored {new_messages} new messages in database")
            return new_messages
        except Exception as e:
            session.rollback()
            logger.error(f"Error storing messages: {str(e)}")
            return 0
        finally:
            session.close()

    def _get_date_range(self, chat_id: str) -> tuple:
        """Get the min and max dates for messages in the database for a specific chat."""
        session = self.Session()
        try:
            # First check if we have any messages for this chat
            message_count = session.query(TelegramMessage).filter(
                TelegramMessage.chat_id == chat_id
            ).count()
            
            if message_count == 0:
                logger.info(f"No messages found in database for chat {chat_id}")
                return None, None
                
            min_date = session.query(func.min(TelegramMessage.date)).filter(
                TelegramMessage.chat_id == chat_id
            ).scalar()
            max_date = session.query(func.max(TelegramMessage.date)).filter(
                TelegramMessage.chat_id == chat_id
            ).scalar()
            
            logger.info(f"Found {message_count} messages in database for {chat_id}")
            logger.info(f"Date range: {min_date} to {max_date}")
            return min_date, max_date
        finally:
            session.close()

    async def fetch_messages(self, chat_urls: List[str], telegram_api_id: str, 
                           telegram_api_hash: str, days_back: int = 1) -> str:
        """Main method to fetch and store Telegram messages."""
        logger.info(f"Starting message fetch for {len(chat_urls)} chats")
        
        # Use real current date, not future date
        end_date = datetime(2024, 4, 28)  # Use a fixed current date for testing
        start_date = end_date - timedelta(days=days_back)
        logger.info(f"Fetching messages from {start_date} to {end_date}")
        
        client = None
        try:
            # Get session string from environment
            session_str = os.getenv('TELEGRAM_SESSION')
            if not session_str:
                raise ValueError("TELEGRAM_SESSION environment variable is not set")
            
            # Remove any comments from the session string
            session_str = session_str.split('#')[0].strip()
            
            # Set up Telegram client with saved session
            client = TelegramClient(StringSession(session_str), telegram_api_id, telegram_api_hash)
            
            # Connect and start client with saved session
            await client.connect()
            if not await client.is_user_authorized():
                raise ValueError("Session is not valid. Please authenticate again.")
            
            # Fetch and store messages
            total_new_messages = 0
            for url in chat_urls:
                # Get chat entity first to get the numeric ID
                chat_name = re.search(r't\.me/([^/]+)', url).group(1)
                chat = await client.get_entity(chat_name)
                chat_id = str(chat.id)
                
                # Get existing date range
                min_date, max_date = self._get_date_range(chat_id)
                
                # Determine date ranges to fetch
                fetch_ranges = []
                if min_date is None or max_date is None:
                    # No messages in database, fetch entire range
                    logger.info(f"No existing messages, fetching entire range from {start_date} to {end_date}")
                    fetch_ranges = [(start_date, end_date)]
                else:
                    # Fetch before min_date if needed
                    if start_date < min_date:
                        logger.info(f"Fetching messages before existing range: {start_date} to {min_date}")
                        fetch_ranges.append((start_date, min_date))
                    # Fetch after max_date if needed
                    if end_date > max_date:
                        logger.info(f"Fetching messages after existing range: {max_date} to {end_date}")
                        fetch_ranges.append((max_date, end_date))
                
                if not fetch_ranges:
                    logger.info(f"No new date ranges to fetch for {chat_id}")
                    continue
                
                # Fetch messages for each range
                for range_start, range_end in fetch_ranges:
                    logger.info(f"Fetching messages from {range_start} to {range_end}")
                    messages = await self._fetch_telegram_messages(client, url, range_start, range_end)
                    new_messages = self._store_messages(messages)
                    total_new_messages += new_messages
            
            return f"Successfully fetched and stored {total_new_messages} new messages from {len(chat_urls)} chats"
            
        except Exception as e:
            logger.error(f"Error in fetch_messages: {str(e)}")
            raise
        
        finally:
            # Ensure client is disconnected
            if client:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.error(f"Error disconnecting client: {str(e)}")

    def fetch_messages_sync(self, chat_urls: List[str], telegram_api_id: str, 
                          telegram_api_hash: str, days_back: int = 1) -> str:
        """Synchronous wrapper for fetch_messages."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self.fetch_messages(
                    chat_urls=chat_urls,
                    telegram_api_id=telegram_api_id,
                    telegram_api_hash=telegram_api_hash,
                    days_back=days_back
                )
            )
            return result
        finally:
            loop.close() 