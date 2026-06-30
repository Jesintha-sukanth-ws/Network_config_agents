#!/usr/bin/env python3
"""
Dashboard Launcher Script

Starts the network automation dashboard and optionally opens the browser.
"""

import subprocess
import time
import webbrowser
import sys
import requests
from pathlib import Path

def check_server_ready(url="http://localhost:8000/dashboard/api/health", timeout=60):
    """Check if the server is ready to serve requests."""
    print("🔍 Waiting for server to be ready...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print("✅ Server is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        print("⏳ Server starting up... (s)")
        time.sleep(5)
    
    print("❌ Server did not start within timeout period")
    return False

def main():
    """Start the dashboard server and optionally open browser."""
    
    # Check if we're in the right directory
    if not Path("app/main.py").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   (where app/main.py exists)")
        sys.exit(1)
    
    print("🚀 Starting Network Operations Dashboard...")
    print("📁 Project directory:", Path.cwd())
    
    try:
        # Start the server
        print("🔧 Starting FastAPI server...")
        server_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000", 
            "--reload"
        ])
        
        # Wait for server to be ready
        if check_server_ready():
            dashboard_url = "http://localhost:8000/dashboard/"
            print(f"🌐 Opening dashboard: {dashboard_url}")
            webbrowser.open(dashboard_url)
            
            print("\n" + "="*60)
            print("🎯 DASHBOARD READY!")
            print(f"   URL: {dashboard_url}")
            print("   Press Ctrl+C to stop the server")
            print("="*60)
            
            # Keep the script running
            try:
                server_process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down server...")
                server_process.terminate()
                server_process.wait()
                print("✅ Server stopped")
        else:
            print("❌ Failed to start server")
            server_process.terminate()
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()