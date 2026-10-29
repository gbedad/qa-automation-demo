import time

import pytest
from playwright.sync_api import expect

import config
from pages import InventoryPage


@pytest.mark.matrix("Login")
def test_login_opens_inventory(login_page, user, page, sauce_url):
    login_page.login(user, config.SAUCE_PASSWORD)

    expect(page).to_have_url(f"{sauce_url}/inventory.html")
    expect(InventoryPage(page, sauce_url).title).to_have_text("Products")


@pytest.mark.matrix("Login time")
def test_login_within_time_budget(login_page, user, page, sauce_url):
    start = time.perf_counter()
    login_page.login(user, config.SAUCE_PASSWORD)
    InventoryPage(page, sauce_url).title.wait_for()
    elapsed = time.perf_counter() - start

    assert elapsed < config.LOGIN_TIME_BUDGET, (
        f"login took {elapsed:.1f}s, budget is {config.LOGIN_TIME_BUDGET:.0f}s"
    )


# Standalone checks: they do not depend on the user profile, so they are
# reported next to the matrices rather than inside them.

def test_locked_out_user_is_rejected(login_page, page, sauce_url):
    login_page.login("locked_out_user", config.SAUCE_PASSWORD)

    expect(login_page.error).to_contain_text("locked out")
    expect(page).to_have_url(f"{sauce_url}/")


def test_wrong_password_is_rejected(login_page):
    login_page.login("standard_user", "not-the-password")

    expect(login_page.error).to_contain_text("do not match")


def test_inventory_requires_login(page, sauce_url):
    page.goto(f"{sauce_url}/inventory.html")

    expect(page.locator('[data-test="error"]')).to_contain_text("inventory.html")
