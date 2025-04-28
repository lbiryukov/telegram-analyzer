import sqlite3
from datetime import datetime

def view_messages():
    # Connect to the SQLite database
    conn = sqlite3.connect('telegram_messages.db')
    cursor = conn.cursor()
    
    # Query all messages
    cursor.execute('''
        SELECT date, chat_title, sender, text 
        FROM telegram_messages 
        ORDER BY date DESC
    ''')
    
    messages = cursor.fetchall()
    
    print(f"\nFound {len(messages)} messages in the database:\n")
    print("-" * 80)
    
    for date, chat_title, sender, text in messages:
        # Convert timestamp to readable format
        date_str = datetime.fromisoformat(date).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Date: {date_str}")
        print(f"Chat: {chat_title}")
        print(f"Sender: {sender}")
        print(f"Message: {text}")
        print("-" * 80)
    
    conn.close()

if __name__ == '__main__':
    view_messages() 