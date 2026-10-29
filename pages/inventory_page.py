import re

from pages.base_page import BasePage


class InventoryPage(BasePage):
    path = "/inventory.html"

    @property
    def title(self):
        return self.by_test_id("title")

    @property
    def items(self):
        return self.by_test_id("inventory-item")

    @property
    def cart_badge(self):
        return self.by_test_id("shopping-cart-badge")

    def item_names(self) -> list[str]:
        return self.by_test_id("inventory-item-name").all_inner_texts()

    def item_prices(self) -> list[float]:
        texts = self.by_test_id("inventory-item-price").all_inner_texts()
        return [float(re.sub(r"[^0-9.]", "", t)) for t in texts]

    def image_sources(self) -> list[str]:
        images = self.page.locator('[data-test="inventory-item"] img')
        return [img.get_attribute("src") or "" for img in images.all()]

    def sort_by(self, option: str):
        """option: 'az', 'za', 'lohi' or 'hilo'."""
        self.by_test_id("product-sort-container").select_option(option)

    def add_to_cart(self, name: str):
        item = self.items.filter(has_text=name)
        item.get_by_role("button", name=re.compile("add to cart", re.I)).click()

    def open_cart(self):
        self.by_test_id("shopping-cart-link").click()
        self.by_test_id("cart-list").wait_for()

    def logout(self):
        self.page.get_by_role("button", name="Open Menu").click()
        self.by_test_id("logout-sidebar-link").click()
