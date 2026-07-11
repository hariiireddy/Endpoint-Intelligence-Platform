"""
sender.py - Sends a telemetry snapshot to the central server.

This is the network half of the agent. It takes the same snapshot dict that
was going into local SQLite and POSTs it to the server's /telemetry endpoint
instead. agent.py calls sender.send() when config.MODE == "server".

Dependency:
    pip install requests
"""

import requests

import config
import os

API_KEY = "0e0c04509284f4c49d9de95b6a7087b3285717971eb3e5caaf3ab6ec04fced95"
REQUEST_TIMEOUT = 10
# Where to send snapshots - built from the base URL in config.py.
TELEMETRY_URL = f"{config.SERVER_URL.rstrip('/')}/telemetry"

# How long to wait for the server before giving up, in seconds. Keeps the
# agent from hanging forever if the server is down or unreachable.
def send(snapshot):
    """POST one snapshot to the server.

    Returns True on success, False on any failure. We never raise: a machine
    that briefly can't reach the server should just skip that snapshot and try
    again next cycle, not crash the agent.
    """
    try:
        response = requests.post(
            TELEMETRY_URL,
            json=snapshot,
            headers={"X-API-Key": API_KEY},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()  # turns HTTP 4xx/5xx into an error
        return True

    except requests.exceptions.ConnectionError:
        print(f"  [sender] could not reach server at {TELEMETRY_URL} "
              "- is it running?")
        return False
    except requests.exceptions.Timeout:
        print(f"  [sender] server took too long to respond "
              f"(>{REQUEST_TIMEOUT}s) - skipping this snapshot")
        return False
    except requests.exceptions.HTTPError as exc:
        print(f"  [sender] server rejected the snapshot: {exc}")
        return False
    except Exception as exc:
        print(f"  [sender] unexpected error sending snapshot: {exc}")
        return False