"""Deterministic test data and the expected results computed from it.

The expected values are computed in Python from the very same rows that are
inserted, so every query is checked against an independent "oracle" rather
than against hard-coded numbers.
"""

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

CITIES = ["Tel Aviv", "Haifa", "Jerusalem", "Paris", "Lyon", "London"]
STATUSES = ["pending", "paid", "shipped", "cancelled"]
N_CUSTOMERS = 1_000
N_ORDERS = 3_000


@dataclass(frozen=True)
class Customer:
    id: int
    name: str
    email: str
    city: str
    created_at: date


@dataclass(frozen=True)
class Order:
    id: int
    customer_id: int
    amount_cents: int
    status: str


def build(seed: int = 42):
    rng = random.Random(seed)
    start = date(2024, 1, 1)
    customers = [
        Customer(
            id=i,
            name=f"Customer {i:04d}",
            email=f"customer{i:04d}@example.com",
            city=rng.choice(CITIES),
            created_at=start + timedelta(days=rng.randrange(700)),
        )
        for i in range(1, N_CUSTOMERS + 1)
    ]
    orders = [
        Order(
            id=i,
            customer_id=rng.randint(1, N_CUSTOMERS),
            amount_cents=rng.randint(500, 50_000),
            status=rng.choice(STATUSES),
        )
        for i in range(1, N_ORDERS + 1)
    ]
    return customers, orders


CUSTOMERS, ORDERS = build()
_BY_ID = {c.id: c for c in CUSTOMERS}


# --- Expected results ----------------------------------------------------------

def expected_customer_ids_in(city: str) -> list[int]:
    return [c.id for c in CUSTOMERS if c.city == city]


def busiest_customer_id() -> int:
    counts = defaultdict(int)
    for o in ORDERS:
        counts[o.customer_id] += 1
    return max(counts, key=lambda cid: (counts[cid], -cid))


def expected_orders_of(customer_id: int) -> list[tuple[int, str, int]]:
    name = _BY_ID[customer_id].name
    return [(o.id, name, o.amount_cents) for o in ORDERS if o.customer_id == customer_id]


def expected_revenue_by_city() -> dict[str, int]:
    revenue = defaultdict(int)
    for o in ORDERS:
        revenue[_BY_ID[o.customer_id].city] += o.amount_cents
    return dict(revenue)


def expected_status_count(status: str, customer_id: int | None = None) -> int:
    return sum(
        1 for o in ORDERS
        if o.status == status and (customer_id is None or o.customer_id == customer_id)
    )
