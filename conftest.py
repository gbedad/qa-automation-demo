import pytest

import config
from api import BookerClient

pytest_plugins = ["reporting.pytest_plugin"]

# The database servers are always installed locally (Docker), like a product
# installed at a customer site: there is nothing to test in remote mode.
collect_ignore = ["tests/db"] if config.MODE == "remote" else []


# --- UI fixtures -------------------------------------------------------------

@pytest.fixture(scope="session")
def sauce_url() -> str:
    return config.SAUCE_URL


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    # A fixed viewport keeps screenshots and layouts comparable between runs.
    return {**browser_context_args, "viewport": {"width": 1280, "height": 800}}


# --- API fixtures ------------------------------------------------------------

@pytest.fixture(scope="session")
def booker_url() -> str:
    return config.BOOKER_URL


@pytest.fixture
def booker(booker_url) -> BookerClient:
    """Unauthenticated client: a fresh session for every test."""
    return BookerClient(booker_url)


@pytest.fixture
def admin_booker(booker_url) -> BookerClient:
    """Client holding a valid admin token (needed for update and delete)."""
    client = BookerClient(booker_url)
    client.authenticate(**config.BOOKER_ADMIN)
    return client
