"""Standalone checks: independent of the dataset, reported next to the matrix."""

import config
from api.datasets import DATASETS


def test_ping(booker):
    assert booker.ping().status_code == 201


def test_valid_credentials_return_token(booker):
    response = booker.create_token(**config.BOOKER_ADMIN)

    assert response.status_code == 200
    assert response.json().get("token")


def test_invalid_credentials_are_rejected(booker):
    response = booker.create_token("admin", "wrong-password")

    assert "token" not in response.json()
    assert response.json().get("reason") == "Bad credentials"


def test_update_without_token_is_forbidden(booker):
    booking_id = booker.create_booking(DATASETS["standard"]).json()["bookingid"]

    response = booker.update_booking(booking_id, DATASETS["no_deposit"])

    assert response.status_code == 403


def test_unknown_booking_returns_404(booker):
    assert booker.get_booking(999_999_999).status_code == 404
