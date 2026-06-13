import subprocess
import time
import os
import sys
import atexit

# ---------------------------------------------------------
# Step 1: Ensure Required Packages are Installed
# ---------------------------------------------------------
# We need python-dotenv to read .env files and pyngrok for the tunnel
try:
    from dotenv import load_dotenv
    from pyngrok import ngrok
except ImportError:
    print("Installing required packages (python-dotenv, pyngrok)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv", "pyngrok", "--quiet"])
    from dotenv import load_dotenv
    from pyngrok import ngrok


# ---------------------------------------------------------
# Step 2: Load Environment Variables
# ---------------------------------------------------------
# This loads the NGROK_AUTHTOKEN from your backend .env file
load_dotenv(os.path.join("gluzo_backend", ".env"))

# Retrieve the token from the environment
NGROK_TOKEN = os.getenv("NGROK_AUTHTOKEN")

if not NGROK_TOKEN:
    print("ERROR: NGROK_AUTHTOKEN not found in gluzo_backend/.env")
    print("Please add it before running this script.")
    sys.exit(1)

# Authenticate ngrok using your token
ngrok.set_auth_token(NGROK_TOKEN)

print("Starting Local Deployment System...")
print("-" * 60)

# Global variables to keep track of our running processes
backend_process = None
frontend_process = None
public_tunnel = None


# ---------------------------------------------------------
# Step 3: Start the FastAPI Backend
# ---------------------------------------------------------
# The backend stays safely on port 8000, hidden from the public.
print("1. Starting FastAPI Backend (Port 8000)...")
backend_process = subprocess.Popen(
    [sys.executable, "run.py"], 
    cwd="gluzo_backend"
)


# ---------------------------------------------------------
# Step 4: Start the Streamlit Frontend
# ---------------------------------------------------------
# The frontend runs on port 8501, which we will expose.
print("2. Starting Streamlit Frontend (Port 8501)...")
frontend_process = subprocess.Popen(
    [sys.executable, "-m", "streamlit", "run", "app.py", 
     "--server.headless", "true", 
     "--server.enableCORS", "false", 
     "--server.enableXsrfProtection", "false"], 
    cwd="streamlit_ui"
)

# Wait a few seconds to let both servers start up completely
print("Waiting for servers to boot up...")
time.sleep(5)


# ---------------------------------------------------------
# Step 5: Start the Ngrok Tunnel (The Magic Step!)
# ---------------------------------------------------------
# We only expose Streamlit (8501). The backend (8000) stays hidden!
print("3. Starting Ngrok Tunnel to expose Streamlit...")
try:
    public_tunnel = ngrok.connect(8501)
except Exception as e:
    print(f"Failed to start Ngrok. Error: {e}")
    # We continue anyway, just in case they still want to use it locally.


# ---------------------------------------------------------
# Step 6: Display the Links to the User
# ---------------------------------------------------------
print("\n" + "="*60)
print("🚀 TEMPORARY DEPLOYMENT IS LIVE!")
print("="*60)

if public_tunnel:
    print(f"🌍 PUBLIC URL (Share this with your interviewer):")
    print(f"   -> {public_tunnel.public_url}")
    print("\n   (This URL forwards securely to your Streamlit frontend.)")
else:
    print("🌍 PUBLIC URL: (Failed to generate, see error above)")

print("\n🏠 LOCAL URLS (For your own testing):")
print(f"   -> Frontend: http://localhost:8501")
print(f"   -> Backend:  http://localhost:8000")
print("="*60 + "\n")
print("Press Ctrl+C to stop all services and close the tunnel.")


# ---------------------------------------------------------
# Step 7: Cleanup on Exit
# ---------------------------------------------------------
def cleanup():
    """
    This function runs automatically when the script stops.
    It ensures we don't leave background processes running.
    """
    print("\nShutting down all services gracefully...")
    
    # Stop the ngrok tunnel
    if public_tunnel:
        print("Closing Ngrok tunnel...")
        try:
            ngrok.disconnect(public_tunnel.public_url)
            ngrok.kill()
        except:
            pass
        
    # Stop the backend and frontend servers
    if backend_process: 
        print("Stopping Backend...")
        backend_process.terminate()
        
    if frontend_process: 
        print("Stopping Frontend...")
        frontend_process.terminate()
        
    print("All processes stopped. Goodbye!")

# Register the cleanup function to run when the script exits
atexit.register(cleanup)


# ---------------------------------------------------------
# Step 8: Keep Script Alive
# ---------------------------------------------------------
try:
    # Keep the script running forever until the user presses Ctrl+C
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nReceived exit signal.")
