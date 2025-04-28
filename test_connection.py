import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_connection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TestConnection')

# Load environment variables
load_dotenv()
logger.info("Loading environment variables")

async def main():
    # Get credentials from environment variables
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    phone_number = os.getenv('TELEGRAM_PHONE')
    password = os.getenv('TELEGRAM_PASSWORD')  # Optional password from env
    
    if not all([api_id, api_hash, phone_number]):
        logger.error("Missing required environment variables")
        return
    
    # Initialize the client
    client = TelegramClient('test_session', api_id, api_hash)
    
    try:
        # Connect to Telegram
        logger.info("Connecting to Telegram...")
        await client.connect()
        
        # Check if we're authorized
        if not await client.is_user_authorized():
            logger.info("Not authorized. Starting authentication...")
            
            # Send code request
            await client.send_code_request(phone_number)
            code = input('Enter the code you received: ')
            
            try:
                # Try to sign in with the code
                await client.sign_in(phone_number, code)
                logger.info("Successfully authenticated with code")
            except Exception as e:
                if "password" in str(e):
                    # If password is needed, try to sign in with password
                    logger.info("Two-step verification is enabled")
                    if password:
                        logger.info("Using password from environment variables")
                        try:
                            await client.sign_in(password=password)
                            logger.info("Successfully authenticated with password")
                        except Exception as e:
                            if "password" in str(e):
                                logger.error("Invalid password from environment variables")
                                password = input('Enter your password: ')
                                await client.sign_in(password=password)
                    else:
                        password = input('Enter your password: ')
                        await client.sign_in(password=password)
                else:
                    raise
        
        # Get the channel
        logger.info("Fetching messages from t.me/thebell_io")
        channel = await client.get_entity('t.me/thebell_io')
        
        # Fetch the last 5 messages
        messages = await client.get_messages(channel, limit=5)
        
        # Print the messages
        logger.info("Last 5 messages from the channel:")
        for message in messages:
            print(f"\nDate: {message.date}")
            print(f"Text: {message.text}")
            print("-" * 50)
            
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    finally:
        await client.disconnect()
        logger.info("Disconnected from Telegram")
        print(f"Session: {StringSession.save(client.session)}")

if __name__ == '__main__':
    asyncio.run(main()) 
    