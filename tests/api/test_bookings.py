import pytest


@pytest.mark.matrix("Create")
def test_create_booking_echoes_payload(booker, dataset):
    _, payload = dataset

    response = booker.create_booking(payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body["bookingid"], int)
    assert body["booking"] == payload


@pytest.mark.matrix("Read")
def test_read_booking(booker, booking):
    booking_id, payload = booking

    response = booker.get_booking(booking_id)

    assert response.status_code == 200
    assert response.json() == payload


@pytest.mark.matrix("Search by name")
def test_search_finds_booking(booker, booking):
    booking_id, payload = booking

    response = booker.list_bookings(
        firstname=payload["firstname"], lastname=payload["lastname"]
    )

    assert response.status_code == 200
    assert booking_id in [b["bookingid"] for b in response.json()]


@pytest.mark.matrix("Full update")
def test_full_update(admin_booker, booking):
    booking_id, payload = booking
    updated = {**payload, "totalprice": payload["totalprice"] + 10, "depositpaid": True}

    response = admin_booker.update_booking(booking_id, updated)

    assert response.status_code == 200, response.text
    assert response.json() == updated
    assert admin_booker.get_booking(booking_id).json() == updated


@pytest.mark.matrix("Partial update")
def test_partial_update(admin_booker, booking):
    booking_id, payload = booking

    response = admin_booker.patch_booking(booking_id, {"additionalneeds": "Dinner"})

    assert response.status_code == 200, response.text
    assert response.json() == {**payload, "additionalneeds": "Dinner"}


@pytest.mark.matrix("Delete")
def test_delete(admin_booker, booking):
    booking_id, _ = booking

    response = admin_booker.delete_booking(booking_id)

    # restful-booker answers 201 Created on a successful delete (documented quirk).
    assert response.status_code == 201
    assert admin_booker.get_booking(booking_id).status_code == 404
