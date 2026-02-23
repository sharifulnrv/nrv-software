import sys
import os
import subprocess

def run_diagnostics():
    print(f"Python Executable: {sys.executable}")
    print(f"Current Directory: {os.getcwd()}")
    print("\n--- sys.path ---")
    for p in sys.path:
        print(p)
    
    print("\n--- Installed Packages (pip list) ---")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list"], capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"Error running pip: {e}")

    print("\n--- Trying to import gspread ---")
    try:
        import gspread
        print("Successfully imported gspread")
        print(f"gspread location: {os.path.dirname(gspread.__file__)}")
    except ImportError as e:
        print(f"ImportError: {e}")

if __name__ == "__main__":
    run_diagnostics()
