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
import sqlite3
import os

app = FastAPI()
security = HTTPBasic()

# Define the Polish timezone
polish_tz = pytz.timezone('Europe/Warsaw')

# Define a simple username and hashed password with reduced rounds for faster verification
USERNAME = "BFF2025"
HASHED_PASSWORD = b"$2b$04$G/pw9saE0cmdW1Ap8p32dO.XjEuiJMS.BWtmQx1xNji3Coem54QaK"

# HTML content cache
html_cache = {}

# Define database path and ensure directory exists
DB_PATH = "/app/data/entries.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        volunteerID TEXT NOT NULL,
        participantHash TEXT NOT NULL,
        registrationPlace TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    ''')
    conn.commit()
    conn.close()

# Call init_db at startup
init_db()

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
    entry.timestamp = datetime.now(polish_tz).isoformat()

    # Save entry to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO entries (volunteerID, participantHash, registrationPlace, timestamp) VALUES (?, ?, ?, ?)",
        (entry.volunteerID, entry.participantHash, entry.registrationPlace, entry.timestamp)
    )
    conn.commit()
    conn.close()

    return {"message": "Entry added successfully"}

@app.get("/entries")
def list_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # This enables column access by name
    cursor = conn.cursor()

    if registrationPlace:
        cursor.execute("SELECT * FROM entries WHERE registrationPlace = ?", (registrationPlace,))
    else:
        cursor.execute("SELECT * FROM entries")

    rows = cursor.fetchall()
    entries_list = []

    for row in rows:
        entries_list.append({
            "volunteerID": row["volunteerID"],
            "participantHash": row["participantHash"],
            "registrationPlace": row["registrationPlace"],
            "timestamp": row["timestamp"]
        })

    conn.close()
    return {"entries": entries_list}

@app.get("/unique-entries")
def list_unique_entries(registrationPlace: Optional[str] = Query(None), credentials: HTTPBasicCredentials = Depends(security)):
    verify_credentials(credentials)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # SQL query to get the latest entry for each unique participantHash
    query = """
    SELECT e.*
    FROM entries e
    INNER JOIN (
        SELECT participantHash, MAX(timestamp) as max_timestamp
        FROM entries
        {}
        GROUP BY participantHash
    ) latest ON e.participantHash = latest.participantHash AND e.timestamp = latest.max_timestamp
    ORDER BY e.timestamp DESC
    """

    if registrationPlace:
        where_clause = "WHERE registrationPlace = ?"
        formatted_query = query.format(where_clause)
        cursor.execute(formatted_query, (registrationPlace,))
    else:
        formatted_query = query.format("")
        cursor.execute(formatted_query)

    rows = cursor.fetchall()
    entries_list = []

    for row in rows:
        entries_list.append({
            "volunteerID": row["volunteerID"],
            "participantHash": row["participantHash"],
            "registrationPlace": row["registrationPlace"],
            "timestamp": row["timestamp"]
        })

    conn.close()
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)