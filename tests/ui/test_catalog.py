import pytest
from playwright.sync_api import expect


@pytest.mark.matrix("Product images")
def test_each_product_has_its_own_image(inventory):
    expect(inventory.items).to_have_count(6)
    sources = inventory.image_sources()

    assert all(sources), "some products have no image"
    assert len(set(sources)) == len(sources), "several products share the same image"


@pytest.mark.matrix("Sort by price")
def test_sort_by_price_low_to_high(inventory):
    inventory.sort_by("lohi")

    prices = inventory.item_prices()
    assert prices == sorted(prices), f"prices not in ascending order: {prices}"


@pytest.mark.matrix("Sort by name")
def test_sort_by_name_z_to_a(inventory):
    inventory.sort_by("za")

    names = inventory.item_names()
    assert names == sorted(names, reverse=True), f"names not in Z-A order: {names}"
