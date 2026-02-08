import requests
import os

BOT_TOKEN = "8560044076:AAE9tHcAuBMY4U521Ynnrf6Y9VIUzahIr0A"
CHAT_ID = "7809021498"

def send_telegram_message(text):
    """Sends a text message to the configured Telegram Chat ID."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False

def send_telegram_document(file_path, caption=None):
    """Sends a document (file) to the configured Telegram Chat ID."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return False
        
    try:
        with open(file_path, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CHAT_ID}
            if caption:
                data['caption'] = caption
            
            response = requests.post(url, data=data, files=files)
            response.raise_for_status()
            return True
    except Exception as e:
        print(f"Error sending Telegram document: {e}")
        return False
