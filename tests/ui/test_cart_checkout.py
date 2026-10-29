import pytest
from playwright.sync_api import expect

from pages import CartPage, CheckoutPage, LoginPage

PRODUCTS = ["Sauce Labs Backpack", "Sauce Labs Bolt T-Shirt"]


@pytest.mark.matrix("Add to cart")
def test_add_two_products_to_cart(inventory, page, sauce_url):
    for name in PRODUCTS:
        inventory.add_to_cart(name)

    expect(inventory.cart_badge).to_have_text(str(len(PRODUCTS)))
    inventory.open_cart()
    assert sorted(CartPage(page, sauce_url).item_names()) == sorted(PRODUCTS)


@pytest.mark.matrix("Checkout")
def test_complete_checkout(inventory, page, sauce_url):
    inventory.add_to_cart(PRODUCTS[0])
    inventory.open_cart()
    CartPage(page, sauce_url).checkout()

    checkout = CheckoutPage(page, sauce_url)
    checkout.fill_information("Gerald", "Tester", "75001")
    expect(page).to_have_url(f"{sauce_url}/checkout-step-two.html")
    checkout.finish()

    expect(checkout.complete_header).to_have_text("Thank you for your order!")


@pytest.mark.matrix("Logout")
def test_logout_returns_to_login(inventory, page, sauce_url):
    inventory.logout()

    expect(page).to_have_url(f"{sauce_url}/")
    expect(LoginPage(page, sauce_url).submit).to_be_visible()
