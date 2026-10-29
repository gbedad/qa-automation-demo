"""The same scenario on every database family and version.

Rows of the matrix follow the life of a database: connect, create it, create
the schema, load rows, query them, change them, check transactions and
constraints, then drop it.
"""

import dataclasses

import pytest

from databases import dataset
from databases.adapters import DuplicateKeyError


@pytest.mark.matrix("Connection")
def test_connects_to_expected_version(server, db_target):
    version = server.server_version()

    # Guards against testing the wrong server: the column must match reality.
    assert version.startswith(db_target.version), (
        f"expected {db_target.family} {db_target.version}, server reports {version}"
    )


@pytest.mark.matrix("Create database")
def test_create_database(server, db_name):
    server.create_database(db_name)
    try:
        assert server.database_exists(db_name)
    finally:
        server.drop_database(db_name)


@pytest.mark.matrix("Create tables")
def test_create_schema(empty_db):
    empty_db.create_schema()

    assert {"customers", "orders"} <= empty_db.table_names()


@pytest.mark.matrix("Insert rows")
def test_insert_rows(schema_db):
    schema_db.insert_customers(dataset.CUSTOMERS)
    schema_db.insert_orders(dataset.ORDERS)

    assert schema_db.count("customers") == dataset.N_CUSTOMERS
    assert schema_db.count("orders") == dataset.N_ORDERS


@pytest.mark.matrix("Query: filter")
@pytest.mark.parametrize("city", ["Haifa", "Paris"])
def test_filter_by_city(seeded_db, city):
    assert seeded_db.customer_ids_in(city) == dataset.expected_customer_ids_in(city)


@pytest.mark.matrix("Query: join")
def test_join_orders_with_customer(seeded_db):
    customer_id = dataset.busiest_customer_id()

    assert seeded_db.orders_of(customer_id) == dataset.expected_orders_of(customer_id)


@pytest.mark.matrix("Query: aggregation")
def test_revenue_by_city(seeded_db):
    assert seeded_db.revenue_by_city() == dataset.expected_revenue_by_city()


@pytest.mark.matrix("Update")
def test_update_order_status(seeded_db):
    customer_id = dataset.busiest_customer_id()
    pending = dataset.expected_status_count("pending", customer_id)

    updated = seeded_db.set_status(customer_id, "pending", "shipped")

    assert updated == pending
    assert seeded_db.count_status("pending", customer_id) == 0
    assert seeded_db.count_status("shipped") == (
        dataset.expected_status_count("shipped") + pending
    )


@pytest.mark.matrix("Transaction rollback")
def test_rollback_leaves_no_rows(seeded_db):
    extra = [
        dataclasses.replace(c, id=c.id + 10_000, email=f"rollback{c.id}@example.com")
        for c in dataset.CUSTOMERS[:50]
    ]

    seeded_db.insert_customers_then_rollback(extra)

    assert seeded_db.count("customers") == dataset.N_CUSTOMERS


@pytest.mark.matrix("Unique constraint")
def test_duplicate_email_is_rejected(seeded_db):
    duplicate = dataclasses.replace(dataset.CUSTOMERS[0], id=99_999)

    with pytest.raises(DuplicateKeyError):
        seeded_db.insert_customers([duplicate])
    assert seeded_db.count("customers") == dataset.N_CUSTOMERS


@pytest.mark.matrix("Drop database")
def test_drop_database(server, seeded_db, db_name):
    seeded_db.close()

    server.drop_database(db_name)

    assert not server.database_exists(db_name)
