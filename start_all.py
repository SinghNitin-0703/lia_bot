import subprocess
import time
import os
import sys
import atexit

try:
    from pyngrok import ngrok
except ImportError:
    print("Installing pyngrok...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
    from pyngrok import ngrok

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

lt_process = None

# 3. Start Ngrok tunneling Streamlit (port 8501)
print("Starting Ngrok tunnel for the UI...")
try:
    from pyngrok.conf import PyngrokConfig
    
    # Set auth token from .env (pyngrok needs this explicitly)
    auth_token = os.getenv("NGROK_AUTHTOKEN")
    if auth_token:
        print(f"Ngrok auth token found.")
    else:
        print("WARNING: NGROK_AUTHTOKEN not found in .env file!")

    # Kill any stale ngrok processes from previous runs
    ngrok.kill()
    time.sleep(2)

    # Configure pyngrok to use v3 config (matches your ngrok.yml version: "3")
    pyngrok_config = PyngrokConfig(
        auth_token=auth_token,
        config_version="3"
    )

    # This exposes port 8501 (Streamlit) to the public web
    public_url = ngrok.connect("8501", pyngrok_config=pyngrok_config, domain="")
    
    print("\n" + "="*60)
    print("SYSTEM IS LIVE!")
    print(f"👉 LOCAL URL: http://localhost:8501")
    print(f"🌍 PUBLIC UI URL: {public_url}")
    print("="*60 + "\n")
    print("Press Ctrl+C to stop all services.")
    
except Exception as e:
    print(f"Ngrok failed (Needs authtoken): {e}")
    print("Falling back to localtunnel (npx localtunnel --port 8501)...")
    try:
        lt_process = subprocess.Popen(
            "npx -y localtunnel --port 8501",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("\n" + "="*60)
        print("SYSTEM IS LIVE!")
        print("👉 FOR LOCAL TESTING (RECOMMENDED): http://localhost:8501")
        print("Wait a few seconds for the Public URL to appear below:")
        print("="*60 + "\n")
        print("Press Ctrl+C to stop all services.\n")
        
        # Read the first line of output to get the URL
        if lt_process.stdout:
            url_line = lt_process.stdout.readline()
            if url_line:
                print(f"🌍 PUBLIC UI URL (May have issues): {url_line.strip()}")
    except Exception as e2:
        print(f"Localtunnel fallback failed: {e2}")

# Ensure we clean up processes when this script closes
def cleanup():
    print("\nShutting down processes...")
    if backend_process: backend_process.terminate()
    if frontend_process: frontend_process.terminate()
    try:
        ngrok.kill()
    except Exception:
        pass
    if lt_process: lt_process.terminate()
    print("All processes stopped.")

atexit.register(cleanup)

try:
    # Keep the script running
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nReceived exit signal.")
