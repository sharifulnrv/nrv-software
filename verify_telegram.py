import sys
import os
from telegram_utils import send_telegram_message, send_telegram_document

def test_telegram():
    print(f"Testing Telegram Bot using telegram_utils...")

    # 1. Test Message
    if send_telegram_message("Hello from Nexus River View! System verification test (updated utils)."):
        print("[SUCCESS] Message sent successfully.")
    else:
        print("[FAILED] Could not send message.")
        return False

    # 2. Test Document (Create a dummy file)
    dummy_file = "test_telegram_doc.txt"
    with open(dummy_file, "w") as f:
        f.write("This is a test document from the verification script.")
        
    try:
        if send_telegram_document(dummy_file, caption='Verification Document'):
             print("[SUCCESS] Document sent successfully.")
        else:
             print("[FAILED] Could not send document.")
             return False
    except Exception as e:
        print(f"[FAILED] Exception: {e}")
        return False
        
    return True

if __name__ == "__main__":
    if test_telegram():
        print("Telegram integration verified.")
    else:
        print("Telegram integration failed.")
        sys.exit(1)
