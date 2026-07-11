"""
server/main.py - The central server. Receives telemetry, stores it, answers
queries, and now scores device health.

CHANGES IN THIS VERSION (code 6): added /devices/{hostname}/health and
/fleet/health, backed by health.py. Everything else is unchanged from code 5.

Run it (from inside the server/ folder):
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Useful URLs:
    /                                health check
    /docs                            interactive API tester
    /devices                         every device + its latest reading
    /devices/NAME                    one device's latest reading
    /devices/NAME/history            one device's recent history
    /devices/NAME/health             one device's health score + warnings
    /fleet/health                    health score for every device
"""

from datetime import datetime

from fastapi import FastAPI, HTTPException

import database
import health

app = FastAPI(title="Endpoint Intelligence Server")


@app.on_event("startup")
def startup():
    database.init_db()


@app.get("/")
def health_check():
    return {
        "status": "ok",
        "service": "endpoint-intelligence-server",
        "snapshots_stored": database.count_snapshots(),
    }


@app.post("/telemetry")
def receive_telemetry(snapshot: dict):
    received_at = datetime.now().isoformat(timespec="seconds")
    database.save_snapshot(snapshot, received_at)
    return {
        "status": "stored",
        "hostname": snapshot.get("hostname"),
        "total_stored": database.count_snapshots(),
    }


# --------------------------------------------------------------------------
# Query endpoints
# --------------------------------------------------------------------------

@app.get("/devices")
def list_devices():
    devices = database.list_devices()
    return {"count": len(devices), "devices": devices}


@app.get("/devices/{hostname}")
def get_device(hostname: str):
    snapshot = database.latest_for_device(hostname)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No data for '{hostname}'")
    return snapshot


@app.get("/devices/{hostname}/history")
def get_device_history(hostname: str, limit: int = 100):
    history = database.history_for_device(hostname, limit=limit)
    if not history:
        raise HTTPException(status_code=404, detail=f"No data for '{hostname}'")
    return {"hostname": hostname, "count": len(history), "history": history}


# --------------------------------------------------------------------------
# Health endpoints - snapshot in, score + warnings out (code 6)
# --------------------------------------------------------------------------

@app.get("/devices/{hostname}/health")
def get_device_health(hostname: str):
    """Score one device based on its latest snapshot."""
    snapshot = database.latest_for_device(hostname)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No data for '{hostname}'")
    return health.evaluate(snapshot)


@app.get("/fleet/health")
def get_fleet_health():
    """Score every device. This is the data the fleet dashboard shows.

    Sorted worst-first so the machines that need attention float to the top.
    """
    reports = [health.evaluate(dev) for dev in database.list_devices()]
    reports.sort(key=lambda r: r["score"])
    return {"count": len(reports), "devices": reports}