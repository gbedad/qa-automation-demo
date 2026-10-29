from pages.base_page import BasePage


class CartPage(BasePage):
    path = "/cart.html"

    @property
    def cart_list(self):
        return self.by_test_id("cart-list")

    def item_names(self) -> list[str]:
        # Scope to the cart list and wait for it: the URL changes before the
        # single-page app re-renders, so reading too early returns the
        # inventory page's products.
        self.cart_list.wait_for()
        return self.cart_list.locator('[data-test="inventory-item-name"]').all_inner_texts()

    def checkout(self):
        self.by_test_id("checkout").click()
