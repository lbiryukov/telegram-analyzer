import streamlit as st
from backend.telegram_analyzer import TelegramAnalyzer, TelegramMessage
from backend.ai_utils import generate_search_keywords
from backend.message_retriever import MessageRetriever
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
from sqlalchemy import func
import json

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

# Initialize analyzers
telegram_analyzer = TelegramAnalyzer()
message_retriever = MessageRetriever()
logger.info("Initializing analyzers")

st.title("Telegram Message Analyzer")

# Create tabs for different functionalities
tab1, tab2 = st.tabs(["Message Fetcher", "Message Analyzer"])

with tab1:
    st.header("Fetch Messages")
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
        elif days_back > 365:
            st.error("Number of days must be less than or equal to 365")
        else:
            try:
                logger.info(f"Starting message fetch for {len(chat_urls)} chats")
                with st.spinner('Fetching messages...'):
                    # Get current date range
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days_back)
                    
                    # Show date range being fetched
                    st.info(f"Fetching messages from {start_date.strftime('%Y-%m-%d %H:%M:%S')} to {end_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    
                    # Create a placeholder for progress updates
                    progress_placeholder = st.empty()
                    
                    # Start time for overall progress
                    start_time = datetime.now()
                    
                    # Create a progress bar
                    progress_bar = st.progress(0)
                    
                    # Function to update progress
                    def update_progress(current, total, time_left):
                        # Ensure total is at least 1 to avoid division by zero
                        total = max(1, total)
                        progress = min(1.0, current / total)
                        progress_bar.progress(progress)
                        
                        # Format time estimate
                        if time_left > 60:
                            time_str = f"{time_left/60:.1f} minutes"
                        else:
                            time_str = f"{time_left:.1f} seconds"
                            
                        # Always show progress, even if time_left is 0
                        if time_left > 0:
                            progress_placeholder.text(f"Progress: {current}/{total} messages (Estimated time left: {time_str})")
                        else:
                            progress_placeholder.text(f"Progress: {current}/{total} messages")
                    
                    # Set up progress tracking
                    update_progress(0, 1, 0)  # Initial state
                    
                    result = telegram_analyzer.fetch_messages_sync(
                        chat_urls=chat_urls,
                        telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                        telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                        days_back=days_back,
                        progress_callback=update_progress
                    )
                    
                    # Get message counts from database
                    session = telegram_analyzer.Session()
                    total_messages = session.query(TelegramMessage).count()
                    messages_in_period = session.query(TelegramMessage).filter(
                        TelegramMessage.date >= start_date,
                        TelegramMessage.date <= end_date
                    ).count()
                    
                    # Get date range in database
                    min_date = session.query(func.min(TelegramMessage.date)).scalar()
                    max_date = session.query(func.max(TelegramMessage.date)).scalar()
                    session.close()
                    
                    # Calculate total time taken
                    total_time = (datetime.now() - start_time).total_seconds()
                    
                    # Clear progress display
                    progress_placeholder.empty()
                    progress_bar.empty()
                    
                    st.success(f"""
                    ✅ {result}
                    
                    📊 Message Statistics:
                    - Total messages in database: {total_messages}
                    - Messages in requested period: {messages_in_period}
                    - Database date range: {min_date.strftime('%Y-%m-%d %H:%M:%S') if min_date else 'None'} to {max_date.strftime('%Y-%m-%d %H:%M:%S') if max_date else 'None'}
                    - Total fetch time: {total_time:.2f} seconds
                    """)
            except Exception as e:
                logger.error(f"Error during message fetch: {str(e)}")
                st.error(f"Error: {str(e)}")

with tab2:
    st.header("Analyze Messages")
    
    # Get list of available chats
    session = telegram_analyzer.Session()
    available_chats = session.query(
        TelegramMessage.chat_id,
        TelegramMessage.chat_title
    ).distinct().all()
    
    # Get date range from database
    min_date = session.query(func.min(TelegramMessage.date)).scalar()
    max_date = session.query(func.max(TelegramMessage.date)).scalar()
    current_date = datetime.now()
    session.close()
    
    # Chat selection
    selected_chat = st.selectbox(
        "Select a chat to analyze",
        options=[(chat_id, title) for chat_id, title in available_chats],
        format_func=lambda x: x[1]
    )
    
    # Date range selection
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            "Start date",
            value=min_date.date() if min_date else datetime.now().date() - timedelta(days=7),
            min_value=min_date.date() if min_date else None,
            max_value=current_date.date()
        )
    with col2:
        end_date = st.date_input(
            "End date",
            value=current_date.date(),
            min_value=min_date.date() if min_date else None,
            max_value=current_date.date()
        )
    
    # Context parameters
    col1, col2 = st.columns(2)
    with col1:
        circ_count = st.number_input(
            "Number of context messages",
            min_value=0,
            max_value=10,
            value=2,
            help="Number of messages to retrieve before and after keyword messages"
        )
    with col2:
        answer_depth = st.number_input(
            "Answer chain depth",
            min_value=0,
            max_value=5,
            value=2,
            help="Maximum depth of answer chains to follow"
        )
    
    # User prompt input
    user_prompt = st.text_area(
        "Enter your question about the messages",
        help="Example: What are the main topics discussed in the last week?",
        height=100
    )
    
    # Initialize session state for keywords if not exists
    if 'keywords' not in st.session_state:
        st.session_state.keywords = []
    
    # Generate keywords button
    if st.button("Generate Keywords"):
        if not user_prompt:
            st.error("Please enter a question")
        else:
            try:
                with st.spinner('Generating search keywords...'):
                    # Generate keywords
                    keywords = generate_search_keywords(user_prompt)
                    st.session_state.keywords = keywords
                    st.success("Generated keywords:")
                    st.write(", ".join(keywords))
            except Exception as e:
                logger.error(f"Error generating keywords: {str(e)}")
                st.error(f"Error: {str(e)}")
    
    # Show keyword adjustment if we have keywords
    if st.session_state.keywords:
        # Add textbox for manual keyword adjustment
        keywords_text = st.text_area(
            "Adjust keywords (comma-separated)",
            value=", ".join(st.session_state.keywords),
            help="You can add, remove, or modify keywords. Separate them with commas.",
            height=100
        )
        
        # Parse keywords from text
        adjusted_keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]
        
        # Retrieve messages button
        if st.button("Retrieve Messages"):
            try:
                # Retrieve messages with context
                with st.spinner('Retrieving messages...'):
                    result = message_retriever.get_messages_with_context(
                        chat_id=selected_chat[0],
                        keywords=adjusted_keywords,
                        start_date=datetime.combine(start_date, datetime.min.time()),
                        end_date=datetime.combine(end_date, datetime.max.time()),
                        circ_count=circ_count,
                        answer_depth_limit=answer_depth
                    )
                    
                    # Display statistics
                    st.subheader("Retrieval Statistics")
                    stats = result['stats']
                    st.json(stats)
                    
                    # Display messages
                    st.subheader("Retrieved Messages")
                    for msg in result['messages']:
                        with st.expander(f"{msg['date']} - {msg['type']}"):
                            st.write(f"**Sender:** {msg['sender']}")
                            st.write(f"**Text:** {msg['text']}")
                    
            except Exception as e:
                logger.error(f"Error during message retrieval: {str(e)}")
                st.error(f"Error: {str(e)}") 