import os
from dotenv import load_dotenv
from backend.telegram_analyzer import TelegramAnalyzer

# Load environment variables
load_dotenv()

def main():
    # Get credentials from environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    
    if not all([api_id, api_hash]):
        print("Error: Missing required environment variables TELEGRAM_API_ID and TELEGRAM_API_HASH")
        return
    
    # Initialize the analyzer
    analyzer = TelegramAnalyzer()
    
    # Example chat URLs to analyze
    chat_urls = [
        't.me/thebell_io'  # Example chat URL
    ]
    
    try:
        # Run the analyzer
        result = analyzer.fetch_messages_sync(
            chat_urls=chat_urls,
            telegram_api_id=api_id,
            telegram_api_hash=api_hash,
            days_back=1  # Analyze last 1 day of messages
        )
        print(result)
    except Exception as e:
        print(f"Error running analyzer: {str(e)}")

if __name__ == '__main__':
    main() 