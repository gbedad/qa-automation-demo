from playwright.sync_api import Page


class BasePage:
    """Shared helpers for every page object."""

    path = "/"

    def __init__(self, page: Page, base_url: str):
        self.page = page
        self.base_url = base_url

    def goto(self):
        self.page.goto(self.base_url + self.path)
        return self

    def by_test_id(self, test_id: str):
        # Saucedemo exposes stable `data-test` attributes, which keep the
        # selectors independent of styling and layout changes.
        return self.page.locator(f'[data-test="{test_id}"]')
