"""
server/database.py - Server-side storage + queries for fleet telemetry.

Holds snapshots from every machine, and provides the read functions the
dashboard needs: list all devices, get one device's latest reading, and
get one device's recent history.
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / "fleet_telemetry.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create the telemetry table if it doesn't exist. Safe to call at startup."""
    conn = get_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS telemetry (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            hostname          TEXT    NOT NULL,
            collected_at      TEXT    NOT NULL,
            received_at       TEXT    NOT NULL,
            cpu_percent       REAL,
            ram_used_percent  REAL,
            disk_used_percent REAL,
            battery_percent   REAL,
            uptime_hours      REAL,
            raw_json          TEXT    NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def save_snapshot(snapshot, received_at):
    """Store one snapshot received from an agent."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO telemetry
            (hostname, collected_at, received_at, cpu_percent,
             ram_used_percent, disk_used_percent, battery_percent,
             uptime_hours, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot.get("hostname"),
            snapshot.get("collected_at"),
            received_at,
            snapshot.get("cpu_percent"),
            snapshot.get("ram_used_percent"),
            snapshot.get("disk_used_percent"),
            snapshot.get("battery_percent"),
            snapshot.get("uptime_hours"),
            json.dumps(snapshot),
        ),
    )
    conn.commit()
    conn.close()


def count_snapshots():
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS n FROM telemetry").fetchone()
    conn.close()
    return row["n"]


# --------------------------------------------------------------------------
# Read functions - these feed the dashboard.
# --------------------------------------------------------------------------

def _row_to_snapshot(row):
    """Turn a database row into the full snapshot dict.

    We return the parsed raw_json (the complete original snapshot) plus the
    server's received_at, so callers get every field the agent ever sent -
    including new ones like SMART that don't have their own columns yet.
    """
    snapshot = json.loads(row["raw_json"])
    snapshot["received_at"] = row["received_at"]
    return snapshot


def list_devices():
    """One row per machine, each with its MOST RECENT snapshot.

    The subquery finds the newest id for each hostname, then we fetch those
    rows. That gives us 'the current state of every device in the fleet',
    which is exactly what the fleet overview page shows.
    """
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT * FROM telemetry
        WHERE id IN (
            SELECT MAX(id) FROM telemetry GROUP BY hostname
        )
        ORDER BY hostname
        """
    ).fetchall()
    conn.close()
    return [_row_to_snapshot(row) for row in rows]


def latest_for_device(hostname):
    """The single most recent snapshot for one machine, or None if unknown."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM telemetry WHERE hostname = ? ORDER BY id DESC LIMIT 1",
        (hostname,),
    ).fetchone()
    conn.close()
    return _row_to_snapshot(row) if row else None


def history_for_device(hostname, limit=100):
    """Recent snapshots for one machine, newest first.

    Used for the per-device detail page and (later) trend-based rules and
    charts. The limit keeps responses reasonable on machines with lots of history.
    """
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM telemetry WHERE hostname = ? ORDER BY id DESC LIMIT ?",
        (hostname, limit),
    ).fetchall()
    conn.close()
    return [_row_to_snapshot(row) for row in rows]