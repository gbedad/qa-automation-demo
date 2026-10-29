import uuid

import pytest

from databases import dataset
from databases.adapters import connect
from databases.targets import DB_REQUIRED, selected_targets

TARGETS = selected_targets()


@pytest.fixture(scope="session", params=TARGETS, ids=[t.id for t in TARGETS])
def db_target(request):
    """Every database test runs once per server version (one matrix column each)."""
    return request.param


@pytest.fixture(scope="session")
def server(db_target):
    """Server-level connection, shared by the tests of one target."""
    try:
        adapter = connect(db_target)
    except Exception as error:  # driver-specific connection errors
        message = (
            f"{db_target.id} not reachable on {db_target.host}:{db_target.port} "
            f"({type(error).__name__}). Start it with: "
            f"docker compose --profile databases up -d --wait"
        )
        if DB_REQUIRED:
            pytest.fail(message)
        pytest.skip(message)
    yield adapter
    adapter.close()


@pytest.fixture
def db_name() -> str:
    return f"qa_{uuid.uuid4().hex[:10]}"


@pytest.fixture
def empty_db(server, db_name):
    """A brand-new, empty database, dropped after the test."""
    server.create_database(db_name)
    db = server.open(db_name)
    yield db
    db.close()
    server.drop_database(db_name)


@pytest.fixture
def schema_db(empty_db):
    empty_db.create_schema()
    return empty_db


@pytest.fixture
def seeded_db(schema_db):
    """Database with the schema and the full dataset loaded."""
    schema_db.insert_customers(dataset.CUSTOMERS)
    schema_db.insert_orders(dataset.ORDERS)
    return schema_db
