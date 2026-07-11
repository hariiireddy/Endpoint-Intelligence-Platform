"""
agent.py - The endpoint intelligence agent. This is the file that gets
deployed to each machine.

It loops forever: collect a snapshot, hand it off, wait, repeat.
WHERE the snapshot goes depends on config.MODE:
    "local"  -> saved to a local SQLite file (database.py)
    "server" -> POSTed to the central server (sender.py)

Run:
    python agent.py
Stop with Ctrl+C.
"""

import time
from datetime import datetime

import collectors
import config


def _handle_local(snapshot):
    """Store the snapshot in the local SQLite database.
    Returns a short status string for the log line.
    """
    import database
    database.save_snapshot(snapshot)
    return f"{database.count_snapshots()} stored locally"


def _handle_server(snapshot):
    """Send the snapshot to the central server via sender.py.
    Returns a short status string for the log line.
    """
    import sender
    ok = sender.send(snapshot)
    return "sent to server" if ok else "SEND FAILED (will retry next cycle)"


def dispatch(snapshot):
    """Route the snapshot based on the configured mode."""
    if config.MODE == "local":
        return _handle_local(snapshot)
    elif config.MODE == "server":
        return _handle_server(snapshot)
    else:
        raise ValueError(
            f"Unknown MODE {config.MODE!r} in config.py. "
            "Use 'local' or 'server'."
        )


def run():
    print(f"Agent started in '{config.MODE}' mode. "
          f"Collecting every {config.COLLECT_INTERVAL_SECONDS}s. "
          "Press Ctrl+C to stop.")

    try:
        while True:
            snapshot = collectors.collect()
            status = dispatch(snapshot)

            now = datetime.now().strftime("%H:%M:%S")
            print(f"[{now}] {snapshot.get('hostname')}: "
                  f"cpu {snapshot.get('cpu_percent')}%, "
                  f"disk {snapshot.get('disk_used_percent')}%  "
                  f"({status})")

            time.sleep(config.COLLECT_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print("\nAgent stopped.")


if __name__ == "__main__":
    run()