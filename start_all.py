import subprocess
import time
import os
import sys
import atexit

try:
    from dotenv import load_dotenv
except ImportError:
    print("Installing python-dotenv...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv

# Load environment variables from the backend .env
load_dotenv(os.path.join("gluzo_backend", ".env"))

print("Starting Gluzo AI System...")

# 1. Start the FastAPI Backend
print("Starting FastAPI Backend on port 8000...")
backend_process = subprocess.Popen(
    [sys.executable, "run.py"], 
    cwd="gluzo_backend"
)

# 2. Start the Streamlit Frontend
print("Starting Streamlit Frontend on port 8501...")
frontend_process = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true", "--server.enableCORS", "false", "--server.enableXsrfProtection", "false"], 
    cwd="streamlit_ui"
)

# Wait a few seconds for the local servers to boot up
time.sleep(5)

print("\n" + "="*60)
print("SYSTEM IS LIVE!")
print(f"-> LOCAL UI URL: http://localhost:8501")
print(f"-> LOCAL API URL: http://localhost:8000")
print("="*60 + "\n")
print("Press Ctrl+C to stop all services.")

# Ensure we clean up processes when this script closes
def cleanup():
    """funxtion summary and flow in very short  """
    print("\nShutting down processes...")
    if backend_process: backend_process.terminate()
    if frontend_process: frontend_process.terminate()
    print("All processes stopped.")

atexit.register(cleanup)

try:
    # Keep the script running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nReceived exit signal.")
