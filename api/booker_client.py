"""Thin client for the restful-booker API.

Keeping HTTP details here lets the tests read like specifications.
"""

import requests


class BookerClient:
    def __init__(self, base_url: str, timeout: float = 15):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "Content-Type": "application/json"}
        )

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # Health and authentication -------------------------------------------
    def ping(self) -> requests.Response:
        return self.session.get(self._url("/ping"), timeout=self.timeout)

    def create_token(self, username: str, password: str) -> requests.Response:
        return self.session.post(
            self._url("/auth"),
            json={"username": username, "password": password},
            timeout=self.timeout,
        )

    def authenticate(self, username: str, password: str) -> str:
        token = self.create_token(username, password).json()["token"]
        self.session.cookies.set("token", token)
        return token

    # Bookings ---------------------------------------------------------------
    def list_bookings(self, **filters) -> requests.Response:
        return self.session.get(
            self._url("/booking"), params=filters, timeout=self.timeout
        )

    def create_booking(self, payload: dict) -> requests.Response:
        return self.session.post(
            self._url("/booking"), json=payload, timeout=self.timeout
        )

    def get_booking(self, booking_id: int) -> requests.Response:
        return self.session.get(
            self._url(f"/booking/{booking_id}"), timeout=self.timeout
        )

    def update_booking(self, booking_id: int, payload: dict) -> requests.Response:
        return self.session.put(
            self._url(f"/booking/{booking_id}"), json=payload, timeout=self.timeout
        )

    def patch_booking(self, booking_id: int, changes: dict) -> requests.Response:
        return self.session.patch(
            self._url(f"/booking/{booking_id}"), json=changes, timeout=self.timeout
        )

    def delete_booking(self, booking_id: int) -> requests.Response:
        return self.session.delete(
            self._url(f"/booking/{booking_id}"), timeout=self.timeout
        )
