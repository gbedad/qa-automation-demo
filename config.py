"""Run configuration, driven by environment variables.

Two modes, mirroring how a product is tested before and after delivery:

* ``local``  - the applications are installed from source in Docker containers
               (``docker compose up``) and tested on localhost, the way a
               customer installation would be validated before going live.
* ``remote`` - the same suite runs against the publicly hosted applications.
"""

import os

MODE = os.getenv("QA_MODE", "local").lower()
if MODE not in ("local", "remote"):
    raise ValueError(f"QA_MODE must be 'local' or 'remote', got {MODE!r}")

_DEFAULTS = {
    "local": {
        "sauce": "http://localhost:3000",
        "booker": "http://localhost:3001",
    },
    "remote": {
        "sauce": "https://www.saucedemo.com",
        "booker": "https://restful-booker.herokuapp.com",
    },
}

SAUCE_URL = os.getenv("SAUCE_URL", _DEFAULTS[MODE]["sauce"]).rstrip("/")
BOOKER_URL = os.getenv("BOOKER_URL", _DEFAULTS[MODE]["booker"]).rstrip("/")

# Public demo credentials published by both applications.
SAUCE_PASSWORD = "secret_sauce"
BOOKER_ADMIN = {"username": "admin", "password": "password123"}

# Saucedemo user profiles: each one simulates a different application behaviour,
# the way each database version can behave differently for the same feature.
SAUCE_USERS = [
    "standard_user",
    "problem_user",
    "performance_glitch_user",
    "error_user",
    "visual_user",
]

# Maximum acceptable login time, in seconds.
LOGIN_TIME_BUDGET = float(os.getenv("LOGIN_TIME_BUDGET", "3"))

RESULTS_DIR = os.getenv("RESULTS_DIR", "reports/results")
