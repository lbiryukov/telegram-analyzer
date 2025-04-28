# Telegram Chat Analyzer

A web application that allows users to analyze Telegram chat messages using AI-powered insights.

## Features

- Input multiple Telegram chat URLs
- Ask questions about the chat content
- AI-powered analysis using CrewAI
- Local storage of chat messages
- Vector-based search using ChromaDB

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root directory with your API keys:
   ```
   TELEGRAM_API_ID=your_telegram_api_id
   TELEGRAM_API_HASH=your_telegram_api_hash
   OPENAI_API_KEY=your_openai_api_key
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Enter Telegram chat URLs (one per line)
2. Enter your question about the chats
3. Click "Analyze" to process
4. View the results in the output window

## Architecture

The application consists of:

- **Frontend**: Streamlit-based web interface
- **Backend**: 
  - Telegram message fetcher
  - SQLite database for message storage
  - ChromaDB for vector-based search
  - CrewAI for AI-powered analysis

## Future Enhancements

- User authentication
- Payment system integration
- Advanced filtering options
- Chat visualization
- Export capabilities

## Requirements

- Python 3.8+
- Telegram API credentials
- OpenAI API key
- Internet connection

## License

MIT License 