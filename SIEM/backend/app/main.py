from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="Custom SIEM")


class LogEvent(BaseModel):
    source: str
    event_type: str
    severity: str
    message: str
    timestamp: datetime

@app.get("/")
def root():
    return {"status": "SIEM Running"}

@app.post("/logs")
def ingest_log(log: LogEvent):
    return {
        "status": "received",
        "data": log
    }