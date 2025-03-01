from fastapi import FastAPI, HTTPException, Depends, status, Query
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from queue import Queue
from datetime import datetime
import pytz
import bcrypt
import secrets

app = FastAPI()
security = HTTPBasic()

# Define the Polish timezone
polish_tz = pytz.timezone('Europe/Warsaw')

# Define a simple username and hashed password
USERNAME = "BFF2025"
HASHED_PASSWORD = b"$2a$12$43fGmfMVH8PhYOHtlb7h5egn8QwrBO0CmglGmgLugCLPf0Y/LGNVW"

def verify_credentials(credentials: HTTPBasicCredentials):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    if not correct_username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Verify the hashed password
    if not bcrypt.checkpw(credentials.password.encode(), HASHED_PASSWORD):
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

# Thread-safe queue for entries
entries_queue = Queue()

@app.post("/entry")
def modify_entry(entry: Entry, credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    entry.timestamp = datetime.now(polish_tz).isoformat()
    entries_queue.put(entry.dict())
    return {"message": "Entry added successfully"}

@app.get("/entries")
def list_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    entries_list = list(entries_queue.queue)

    # Filter entries by registrationPlace if the parameter is provided
    if registrationPlace:
        entries_list = [entry for entry in entries_list if entry['registrationPlace'] == registrationPlace]

    return {"entries": entries_list}

@app.get("/unique-entries")
def list_unique_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    entries_list = list(entries_queue.queue)

    # Filter entries by registrationPlace if the parameter is provided
    if registrationPlace:
        entries_list = [entry for entry in entries_list if entry['registrationPlace'] == registrationPlace]

    # Dictionary to store the latest entry for each unique participant hash
    unique_entries = {}

    # Process entries in chronological order (older to newer)
    for entry in entries_list:
        participant_hash = entry['participantHash']
        # Always update the entry in the dictionary,
        # which will ensure we keep the most recent one
        unique_entries[participant_hash] = entry

    # Convert back to list (values of the dictionary)
    deduplicated_entries = list(unique_entries.values())

    # Sort by timestamp (newest first)
    deduplicated_entries.sort(key=lambda x: x['timestamp'], reverse=True)

    return {"entries": deduplicated_entries}

@app.get("/registration", response_class=HTMLResponse)
def get_register(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of register.html
    with open("/app/static/registration.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/status", response_class=HTMLResponse)
def get_status(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of status.html
    with open("/app/static/status.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/index", response_class=HTMLResponse)
def get_status(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of status.html
    with open("/app/static/index.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/settings", response_class=HTMLResponse)
def get_status(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of status.html
    with open("/app/static/settings.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/stats", response_class=HTMLResponse)
def get_status(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of status.html
    with open("/app/static/stats.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/info", response_class=HTMLResponse)
def get_status(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Read the content of status.html
    with open("/app/static/info.html", "r") as file:
        html_content = file.read()
    return HTMLResponse(content=html_content, status_code=200)

@app.get("/pepe.ico")
def get_icon(credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)
    # Return the .ico file using FileResponse
    return FileResponse(path="/app/static/pepe.ico", media_type="image/x-icon")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
