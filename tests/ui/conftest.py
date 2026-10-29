import pytest

import config
from pages import InventoryPage, LoginPage


@pytest.fixture(params=config.SAUCE_USERS)
def user(request) -> str:
    """Every matrix test runs once per user profile (one matrix column each)."""
    return request.param


@pytest.fixture
def login_page(page, sauce_url) -> LoginPage:
    return LoginPage(page, sauce_url).goto()


@pytest.fixture
def inventory(login_page, user, page, sauce_url) -> InventoryPage:
    """Logged-in inventory page for the current user profile."""
    login_page.login(user, config.SAUCE_PASSWORD)
    inventory = InventoryPage(page, sauce_url)
    inventory.title.wait_for()
    return inventory


# Run (and therefore report) the UI tests in the order of a user journey:
# log in, browse, buy, log out.
_JOURNEY = ["test_login.py", "test_catalog.py", "test_cart_checkout.py"]


def pytest_collection_modifyitems(items):
    def rank(item):
        name = item.path.name
        return _JOURNEY.index(name) if name in _JOURNEY else len(_JOURNEY)

    items.sort(key=rank)  # stable sort keeps the order inside each file
