import copy

import pytest

from api.datasets import DATASETS


@pytest.fixture(params=list(DATASETS), ids=list(DATASETS))
def dataset(request) -> tuple[str, dict]:
    """Every matrix test runs once per dataset (one matrix column each)."""
    return request.param, copy.deepcopy(DATASETS[request.param])


@pytest.fixture
def booking(booker, admin_booker, dataset):
    """A booking created for the test and removed afterwards."""
    _, payload = dataset
    response = booker.create_booking(payload)
    assert response.status_code == 200, response.text
    booking_id = response.json()["bookingid"]

    yield booking_id, payload

    admin_booker.delete_booking(booking_id)  # no-op if the test already deleted it
