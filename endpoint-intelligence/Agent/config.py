"""
config.py - Settings for the agent. This is the one file you edit to change
how the agent behaves. Keeping settings here (not scattered in code) means
deploying to the fleet is just shipping this file with the right values.
"""

# MODE decides where snapshots go:
#   "local"  -> save to a local SQLite file (offline testing, single machine)
#   "server" -> POST to the central server (real deployment)
#
# Right now use "local". Switch to "server" after code 4 (sender.py) exists
# and your server (code 3) is running.
MODE = "server"

# The central server's base URL. Only used in "server" mode.
# During testing the server runs on your own machine, hence localhost:8000.
# For real deployment, replace with the server's address, e.g.
#   "http://192.168.1.50:8000"  or  "https://health.yourcompany.local"
SERVER_URL = "http://52.0.117.105:8000"

# How often to collect a snapshot, in seconds.
#   60  = once a minute (good while testing, you see activity fast)
#   300 = every 5 minutes (sensible for real fleet use)
COLLECT_INTERVAL_SECONDS = 60