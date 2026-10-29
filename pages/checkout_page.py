from pages.base_page import BasePage


class CheckoutPage(BasePage):
    path = "/checkout-step-one.html"

    def fill_information(self, first: str, last: str, postal_code: str):
        self.by_test_id("firstName").fill(first)
        self.by_test_id("lastName").fill(last)
        self.by_test_id("postalCode").fill(postal_code)
        self.by_test_id("continue").click()

    def finish(self):
        self.by_test_id("finish").click()

    @property
    def complete_header(self):
        return self.by_test_id("complete-header")

    @property
    def error(self):
        return self.by_test_id("error")
