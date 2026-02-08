import requests
import sys

# Constants from your setup
BOT_TOKEN = "8560044076:AAE9tHcAuBMY4U521Ynnrf6Y9VIUzahIr0A"
CHAT_ID = "7809021498"

def test_telegram():
    print(f"Testing Telegram Bot...")
    print(f"Token: {BOT_TOKEN[:10]}...")
    print(f"Chat ID: {CHAT_ID}")

    # 1. Test Message
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": "Hello from Nexus River View! System verification test."
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        print("[SUCCESS] Message sent successfully.")
    except Exception as e:
        print(f"[FAILED] Could not send message: {e}")
        return False

    # 2. Test Document (Create a dummy file)
    dummy_file = "test_telegram_doc.txt"
    with open(dummy_file, "w") as f:
        f.write("This is a test document from the verification script.")
        
    url_doc = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    try:
        with open(dummy_file, 'rb') as f:
            files = {'document': f}
            data = {'chat_id': CHAT_ID, 'caption': 'Verification Document'}
            response = requests.post(url_doc, data=data, files=files)
            response.raise_for_status()
        print("[SUCCESS] Document sent successfully.")
    except Exception as e:
        print(f"[FAILED] Could not send document: {e}")
        return False
        
    return True

if __name__ == "__main__":
    if test_telegram():
        print("Telegram integration verified.")
    else:
        print("Telegram integration failed.")
        sys.exit(1)
