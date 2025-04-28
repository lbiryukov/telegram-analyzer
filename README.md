# Telegram Message Analyzer

A Python application to fetch and analyze messages from Telegram channels using the Telethon library and SQLite database.

## Features

- Fetch messages from multiple Telegram channels
- Store messages in SQLite database
- Efficient message fetching with date range filtering
- Web interface using Streamlit
- Message deduplication
- Date range based message retrieval

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your Telegram API credentials:
```
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION=your_session_string
```

3. Run the application:
```bash
streamlit run app.py
```

## Usage

1. Enter one or more Telegram channel URLs (e.g., https://t.me/channel_name)
2. Specify how many days of messages to fetch
3. Click "Fetch Messages" to start the process

The application will:
- Check for existing messages in the database
- Only fetch messages from date ranges that aren't already stored
- Show statistics about fetched messages

## Files

- `app.py`: Streamlit web interface
- `backend/telegram_analyzer.py`: Main message fetching and database logic
- `recreate_db.py`: Utility to recreate the database
- `test_db.py`: Database testing and inspection tool

## Requirements

- Python 3.7+
- Telethon
- SQLAlchemy
- Streamlit
- python-dotenv 