import os
import requests
from decouple import config

# --- Configuration ---
# These will be read from your environment variables in Dokploy
TELEGRAM_BOT_TOKEN = config('TELEGRAM_BOT_TOKEN', default=None)
TELEGRAM_CHAT_ID = config('TELEGRAM_CHAT_ID', default=None)

def send_message(message_text):
    """Sends a message to the configured Telegram chat."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram environment variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set.")
        return

    # Using the Telegram Bot API endpoint
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown' # Allows for bold, italics, etc.
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("SUCCESS: Message sent to Telegram.")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to send message to Telegram. Error: {e}")

if __name__ == '__main__':
    # This is for testing the Telegram bot directly
    print("Testing Telegram bot...")
    send_message("Hello from the Market Intel Bot! The connection is working.")
    print("Test complete.")
  
