import sys
import threading
import time
import os
import subprocess
import socket
import json
import tkinter as tk
from tkinter import filedialog
from app import create_app

def get_app_data_path():
    app_data = os.getenv('APPDATA')
    if not app_data:
        app_data = os.path.expanduser("~")
    path = os.path.join(app_data, 'NexusRiverView')
    os.makedirs(path, exist_ok=True)
    return path

def get_launcher_config():
    config_path = os.path.join(get_app_data_path(), 'launcher_config.json')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_launcher_config(config):
    config_path = os.path.join(get_app_data_path(), 'launcher_config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f)

def select_data_folder():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    folder_selected = filedialog.askdirectory(title="Select Data Folder for Nexus River View")
    root.destroy()
    return folder_selected

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_server():
    if is_port_in_use(5001):
        print("Server already running on port 5001.")
        return
    
    print("Starting Flask server...")
    app = create_app()
    app.run(host='127.0.0.1', port=5001, use_reloader=False)

def launch_app_window(url):
    """Launch the browser in 'App Mode' to make it look like standalone software."""
    edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if not os.path.exists(edge_path):
        edge_path = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"

    # Try Edge App Mode first (installed on all Windows)
    if os.path.exists(edge_path):
        print("Launching Edge in App Mode...")
        subprocess.Popen([edge_path, f"--app={url}", "--window-size=1280,800"])
    # Try Chrome App Mode
    elif os.path.exists(chrome_path):
        print("Launching Chrome in App Mode...")
        subprocess.Popen([chrome_path, f"--app={url}"])
    # Final Fallback
    else:
        print("No browser app mode found, opening in default browser.")
        import webbrowser
        webbrowser.open(url)

if __name__ == '__main__':
    # 0. Load .env
    from dotenv import load_dotenv
    load_dotenv()
    
    # 1. Setup Data Path with refined priorities:
    # Priority 1: Persistent config from APPDATA
    launcher_config = get_launcher_config()
    data_path = launcher_config.get('data_path')
    
    # Priority 2: Check .env if no persistent config
    if not data_path or not os.path.exists(data_path):
        data_path = os.environ.get('NEXUS_DATA_PATH')
        
    # Priority 3: Prompt user if .env is missing/relative or invalid
    if not data_path or data_path == '.' or not os.path.isabs(data_path) or not os.path.exists(data_path):
        # Determine fallback default
        default_nrv_path = r"C:\NRV_2" # Updated to match user request
        
        if os.path.exists(default_nrv_path):
            data_path = default_nrv_path
        else:
            # Last resort: ask the user
            print("No valid data path found. Please select a folder.")
            data_path = select_data_folder()
            
    if not data_path:
        print("Error: No data folder selected. Exiting.")
        sys.exit(1)
            
    # Save the selected path for next time
    launcher_config['data_path'] = data_path
    save_launcher_config(launcher_config)

    os.environ['NEXUS_DATA_PATH'] = data_path
    print(f"Using Data Path: {data_path}")

    # 2. Start Server in Background
    t = threading.Thread(target=start_server, daemon=True)
    t.start()

    # 3. Wait for Server to be actually ready
    print("Waiting for server to initialize...")
    url = "http://127.0.0.1:5001/"
    timeout = 30
    start_time = time.time()
    
    while not is_port_in_use(5001):
        time.sleep(0.5)
        if time.time() - start_time > timeout:
            print("Timeout waiting for server.")
            sys.exit(1)
    
    # Give it a tiny extra buffer for Flask to finish routing setup
    time.sleep(1)

    # Start ngrok tunnel for remote access in background (hidden)
    try:
        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(['ngrok', 'http', '5001'], creationflags=CREATE_NO_WINDOW)
        print("Ngrok tunnel started in background.")
    except Exception as e:
        print(f"Could not start ngrok: {e}")

    # 4. Launch the "Software Window"
    launch_app_window(url)
    
    print("Software started. (Close this console window to stop the server if needed)")
    
    # Keep the main process alive so the server thread continues
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
