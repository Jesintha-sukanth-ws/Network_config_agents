from fastapi import FastAPI
import threading
from app.services.polling_service import poll_servicenow


app = FastAPI()

# Start polling in background thread
def start_polling():
    poll_servicenow()

polling_thread = threading.Thread(target=start_polling, daemon=True)
polling_thread.start()

print(" Polling service running in background")
