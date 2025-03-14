from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime
import pytz
import bcrypt
import secrets
from functools import lru_cache
import threading
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bff-app")

app = FastAPI()
security = HTTPBasic()

# Define the Polish timezone
polish_tz = pytz.timezone('Europe/Warsaw')

# Define a simple username and hashed password with reduced rounds for faster verification
USERNAME = "BFF2025"
HASHED_PASSWORD = b"$2b$04$G/pw9saE0cmdW1Ap8p32dO.XjEuiJMS.BWtmQx1xNji3Coem54QaK"

# HTML content cache
html_cache = {}

# In-memory data structures with copy-on-write strategy
class InMemoryDB:
    def __init__(self):
        # Main list of all entries - no need for copy during reads
        self._entries = []

        # Dictionary for fast lookup of latest entries by participantHash
        self._unique_entries = {}

        # Pre-computed filtered entries by place
        self._entries_by_place = {}

        # Pre-computed filtered unique entries by place
        self._unique_entries_by_place = {}

        # Lock only used during writes
        self.write_lock = threading.Lock()

    def add_entry(self, entry):
        with self.write_lock:
            # Create full entry
            full_entry = {
                "volunteerID": entry.volunteerID,
                "participantHash": entry.participantHash,
                "registrationPlace": entry.registrationPlace,
                "timestamp": entry.timestamp
            }

            # Add to main entries list
            self._entries.append(full_entry)

            # Update unique entries dictionary with latest entry
            self._unique_entries[entry.participantHash] = full_entry

            # Clear all caches after adding a new entry
            self._entries_by_place = {}
            self._unique_entries_by_place = {}

            return full_entry

    def get_all_entries(self):
        # No lock needed for read operations
        # Return sorted entries (newest first)
        # No need to make a copy since we never modify existing entries
        return sorted(self._entries, key=lambda x: x["timestamp"], reverse=True)

    def get_entries_by_place(self, place):
        # Try to get from cache first
        entries_by_place = self._entries_by_place  # Take a local reference to avoid race conditions
        if place in entries_by_place:
            return entries_by_place[place]  # Return cached result if available

        # Not in cache, compute and store
        filtered = [entry for entry in self._entries if entry["registrationPlace"] == place]
        sorted_entries = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)

        # Store in cache - no lock needed as we're only adding to a dict
        # If another thread already added this, it's fine
        self._entries_by_place[place] = sorted_entries

        return sorted_entries

    def get_unique_entries(self):
        # No lock needed - the dictionary values are never modified
        # Return sorted unique entries (newest first)
        return sorted(list(self._unique_entries.values()), key=lambda x: x["timestamp"], reverse=True)

    def get_unique_entries_by_place(self, place):
        # Try to get from cache first
        unique_entries_by_place = self._unique_entries_by_place  # Take a local reference
        if place in unique_entries_by_place:
            return unique_entries_by_place[place]  # Return cached result if available

        # Not in cache, compute and store
        filtered = [
            entry for entry in self._unique_entries.values()
            if entry["registrationPlace"] == place
        ]
        sorted_entries = sorted(filtered, key=lambda x: x["timestamp"], reverse=True)

        # Store in cache - no lock needed as we're only adding to a dict
        self._unique_entries_by_place[place] = sorted_entries

        return sorted_entries

# Create the in-memory database
db = InMemoryDB()

def get_html_content(file_path):
    """Get HTML content from cache or read from file if not cached"""
    if file_path not in html_cache:
        with open(file_path, "r") as file:
            html_cache[file_path] = file.read()
    return html_cache[file_path]

@lru_cache(maxsize=128)
def cached_check_password(password_str):
    """Cache password verification results for better performance"""
    return bcrypt.checkpw(password_str.encode(), HASHED_PASSWORD)

def verify_credentials(credentials: HTTPBasicCredentials):
    # Fast username check first (fails fast if username is wrong)
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    if not correct_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Use cached password verification
    if not cached_check_password(credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

class Entry(BaseModel):
    volunteerID: str
    participantHash: str
    registrationPlace: str
    timestamp: Optional[str] = Field(default=None)

@app.post("/entry")
def modify_entry(entry: Entry, credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)

    # Set timestamp if not provided
    if not entry.timestamp:
        entry.timestamp = datetime.now(polish_tz).isoformat()

    # Add entry to in-memory database
    db.add_entry(entry)

    logger.info(f"New entry added: participantHash={entry.participantHash}, place={entry.registrationPlace}")

    return {"message": "Entry added successfully"}

@app.get("/entries")
def list_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)

    if registrationPlace:
        entries_list = db.get_entries_by_place(registrationPlace)
        logger.info(f"Retrieved {len(entries_list)} entries for place: {registrationPlace}")
    else:
        entries_list = db.get_all_entries()
        logger.info(f"Retrieved all {len(entries_list)} entries")

    return {"entries": entries_list}

@app.get("/unique-entries")
def list_unique_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)

    if registrationPlace:
        entries_list = db.get_unique_entries_by_place(registrationPlace)
        logger.info(f"Retrieved {len(entries_list)} unique entries for place: {registrationPlace}")
    else:
        entries_list = db.get_unique_entries()
        logger.info(f"Retrieved all {len(entries_list)} unique entries")

    return {"entries": entries_list}

@app.get("/registration", response_class=HTMLResponse)
def get_register(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/registration.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/status", response_class=HTMLResponse)
def get_status_page(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/status.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/index", response_class=HTMLResponse)
def get_index(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/index.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/settings", response_class=HTMLResponse)
def get_settings(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/settings.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/stats", response_class=HTMLResponse)
def get_stats(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/stats.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/info", response_class=HTMLResponse)
def get_info(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    html_content = get_html_content("/app/static/info.html")
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/pepe.ico")
def get_icon(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Return the .ico file using FileResponse
    return FileResponse(path="/app/static/pepe.ico", media_type="image/x-icon")

# Add startup event handler to log "Hello world"
@app.on_event("startup")
async def startup_event():
    logger.info("Hello world")
    logger.info("Application started successfully")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)