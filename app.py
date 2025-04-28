import streamlit as st
from backend.telegram_analyzer import TelegramAnalyzer, TelegramMessage
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from sqlalchemy import func

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('streamlit_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('StreamlitApp')

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

# Initialize TelegramAnalyzer
analyzer = TelegramAnalyzer()
logger.info("Initializing TelegramAnalyzer")

st.title("Telegram Message Fetcher")

# Input fields
chat_urls = st.text_area(
    "Enter Telegram chat URLs (one per line)",
    help="Example: https://t.me/chatname"
).split('\n')

# Remove empty lines
chat_urls = [url.strip() for url in chat_urls if url.strip()]

days_back = st.number_input(
    "Number of days to look back",
    min_value=1,
    max_value=365,
    value=1
)

if st.button("Fetch Messages"):
    if not chat_urls:
        st.error("Please enter at least one chat URL")
    else:
        try:
            logger.info(f"Starting message fetch for {len(chat_urls)} chats")
            with st.spinner('Fetching messages...'):
                # Get current date range
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days_back)
                
                # Show date range being fetched
                st.info(f"Fetching messages from {start_date.strftime('%Y-%m-%d %H:%M:%S')} to {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                result = analyzer.fetch_messages_sync(
                    chat_urls=chat_urls,
                    telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                    telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                    days_back=days_back
                )
                
                # Get message counts from database
                session = analyzer.Session()
                total_messages = session.query(TelegramMessage).count()
                messages_in_period = session.query(TelegramMessage).filter(
                    TelegramMessage.date >= start_date,
                    TelegramMessage.date <= end_date
                ).count()
                
                # Get date range in database
                min_date = session.query(func.min(TelegramMessage.date)).scalar()
                max_date = session.query(func.max(TelegramMessage.date)).scalar()
                session.close()
                
                st.success(f"""
                ✅ {result}
                
                📊 Message Statistics:
                - Total messages in database: {total_messages}
                - Messages in requested period: {messages_in_period}
                - Database date range: {min_date.strftime('%Y-%m-%d %H:%M:%S') if min_date else 'None'} to {max_date.strftime('%Y-%m-%d %H:%M:%S') if max_date else 'None'}
                """)
        except Exception as e:
            logger.error(f"Error during message fetch: {str(e)}")
            st.error(f"Error: {str(e)}") 