"""One adapter per database family, all exposing the same operations.

The tests only talk to this interface, so the exact same scenario runs on
PostgreSQL, MySQL and MongoDB, and on every version of each.
"""

from dataclasses import asdict

from databases.dataset import Customer, Order
from databases.targets import PASSWORD, USER, Target


class DuplicateKeyError(Exception):
    """Raised by every adapter when a unique constraint rejects a row."""


class DatabaseAdapter:
    def __init__(self, target: Target, database: str | None = None):
        self.target = target
        self.database = database

    # Server level
    def server_version(self) -> str: ...
    def create_database(self, name: str) -> None: ...
    def database_exists(self, name: str) -> bool: ...
    def drop_database(self, name: str) -> None: ...
    def open(self, name: str) -> "DatabaseAdapter": ...
    def close(self) -> None: ...

    # Database level
    def create_schema(self) -> None: ...
    def table_names(self) -> set[str]: ...
    def insert_customers(self, rows: list[Customer]) -> None: ...
    def insert_orders(self, rows: list[Order]) -> None: ...
    def count(self, table: str) -> int: ...
    def customer_ids_in(self, city: str) -> list[int]: ...
    def orders_of(self, customer_id: int) -> list[tuple[int, str, int]]: ...
    def revenue_by_city(self) -> dict[str, int]: ...
    def set_status(self, customer_id: int, old: str, new: str) -> int: ...
    def count_status(self, status: str, customer_id: int | None = None) -> int: ...
    def insert_customers_then_rollback(self, rows: list[Customer]) -> None: ...


# --- SQL ------------------------------------------------------------------------

class SqlAdapter(DatabaseAdapter):
    """Shared SQL; both drivers use the %s placeholder style."""

    SCHEMA = [
        """CREATE TABLE customers (
               id INT PRIMARY KEY,
               name VARCHAR(100) NOT NULL,
               email VARCHAR(255) NOT NULL UNIQUE,
               city VARCHAR(50) NOT NULL,
               created_at DATE NOT NULL)""",
        """CREATE TABLE orders (
               id INT PRIMARY KEY,
               customer_id INT NOT NULL,
               amount_cents INT NOT NULL,
               status VARCHAR(20) NOT NULL,
               FOREIGN KEY (customer_id) REFERENCES customers (id))""",
        "CREATE INDEX idx_orders_customer ON orders (customer_id)",
    ]

    def __init__(self, target, database=None):
        super().__init__(target, database)
        self.conn = self._connect(database)

    def _connect(self, database): ...
    def _is_duplicate(self, error: Exception) -> bool: ...

    def _query(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def _execute(self, sql, params=()):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount

    def close(self):
        if self.conn is not None:
            self.conn.close()
            self.conn = None

    def create_schema(self):
        for statement in self.SCHEMA:
            self._execute(statement)

    def insert_customers(self, rows):
        try:
            with self.conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO customers (id, name, email, city, created_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    [(c.id, c.name, c.email, c.city, c.created_at) for c in rows],
                )
        except Exception as error:
            if self._is_duplicate(error):
                raise DuplicateKeyError(str(error)) from error
            raise

    def insert_orders(self, rows):
        with self.conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO orders (id, customer_id, amount_cents, status) "
                "VALUES (%s, %s, %s, %s)",
                [(o.id, o.customer_id, o.amount_cents, o.status) for o in rows],
            )

    def count(self, table):
        assert table in ("customers", "orders")
        return self._query(f"SELECT COUNT(*) FROM {table}")[0][0]

    def customer_ids_in(self, city):
        rows = self._query("SELECT id FROM customers WHERE city = %s ORDER BY id", (city,))
        return [r[0] for r in rows]

    def orders_of(self, customer_id):
        rows = self._query(
            "SELECT o.id, c.name, o.amount_cents FROM orders o "
            "JOIN customers c ON c.id = o.customer_id "
            "WHERE c.id = %s ORDER BY o.id",
            (customer_id,),
        )
        return [(r[0], r[1], r[2]) for r in rows]

    def revenue_by_city(self):
        rows = self._query(
            "SELECT c.city, SUM(o.amount_cents) FROM orders o "
            "JOIN customers c ON c.id = o.customer_id GROUP BY c.city"
        )
        return {city: int(total) for city, total in rows}

    def set_status(self, customer_id, old, new):
        return self._execute(
            "UPDATE orders SET status = %s WHERE customer_id = %s AND status = %s",
            (new, customer_id, old),
        )

    def count_status(self, status, customer_id=None):
        if customer_id is None:
            return self._query("SELECT COUNT(*) FROM orders WHERE status = %s", (status,))[0][0]
        return self._query(
            "SELECT COUNT(*) FROM orders WHERE status = %s AND customer_id = %s",
            (status, customer_id),
        )[0][0]


class PostgresAdapter(SqlAdapter):
    def _connect(self, database):
        import psycopg

        return psycopg.connect(
            host=self.target.host, port=self.target.port,
            user=USER["postgres"], password=PASSWORD,
            dbname=database or "postgres", autocommit=True, connect_timeout=5,
        )

    def _is_duplicate(self, error):
        import psycopg

        return isinstance(error, psycopg.errors.UniqueViolation)

    def server_version(self):
        return self._query("SHOW server_version")[0][0]

    def create_database(self, name):
        self._execute(f'CREATE DATABASE "{name}"')

    def database_exists(self, name):
        return bool(self._query("SELECT 1 FROM pg_database WHERE datname = %s", (name,)))

    def drop_database(self, name):
        self._execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')

    def open(self, name):
        return PostgresAdapter(self.target, name)

    def table_names(self):
        rows = self._query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
        )
        return {r[0] for r in rows}

    def insert_customers_then_rollback(self, rows):
        class Abort(Exception):
            pass

        try:
            with self.conn.transaction():
                self.insert_customers(rows)
                raise Abort
        except Abort:
            pass


class MySqlAdapter(SqlAdapter):
    def _connect(self, database):
        import pymysql

        return pymysql.connect(
            host=self.target.host, port=self.target.port,
            user=USER["mysql"], password=PASSWORD,
            database=database, autocommit=True, connect_timeout=5,
        )

    def _is_duplicate(self, error):
        import pymysql

        return isinstance(error, pymysql.err.IntegrityError) and error.args[0] == 1062

    def server_version(self):
        return self._query("SELECT VERSION()")[0][0]

    def create_database(self, name):
        self._execute(f"CREATE DATABASE `{name}` CHARACTER SET utf8mb4")

    def database_exists(self, name):
        return bool(self._query(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (name,)
        ))

    def drop_database(self, name):
        self._execute(f"DROP DATABASE IF EXISTS `{name}`")

    def open(self, name):
        return MySqlAdapter(self.target, name)

    def table_names(self):
        rows = self._query(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
            (self.database,),
        )
        return {r[0] for r in rows}

    def insert_customers_then_rollback(self, rows):
        self.conn.begin()
        try:
            self.insert_customers(rows)
        finally:
            self.conn.rollback()


# --- MongoDB ----------------------------------------------------------------------

class MongoAdapter(DatabaseAdapter):
    """Collections play the role of tables; $lookup plays the role of JOIN.

    Transactions need a replica set: the containers run as single-node
    replica sets (see docker-compose.yml).
    """

    def __init__(self, target, database=None, client=None):
        super().__init__(target, database)
        if client is None:
            from pymongo import MongoClient

            client = MongoClient(
                target.host, target.port, directConnection=True,
                serverSelectionTimeoutMS=5000,
            )
            client.admin.command("ping")
        self.client = client
        self.db = client[database] if database else None

    def server_version(self):
        return self.client.server_info()["version"]

    def create_database(self, name):
        # MongoDB creates a database lazily, with its first collection.
        self.client[name].create_collection("_created")

    def database_exists(self, name):
        return name in self.client.list_database_names()

    def drop_database(self, name):
        self.client.drop_database(name)

    def open(self, name):
        return MongoAdapter(self.target, name, client=self.client)

    def close(self):
        if self.database is None:  # only the server-level adapter owns the client
            self.client.close()

    def create_schema(self):
        self.db.create_collection("customers")
        self.db.create_collection("orders")
        self.db.customers.create_index("email", unique=True)
        self.db.orders.create_index("customer_id")

    def table_names(self):
        return set(self.db.list_collection_names()) - {"_created"}

    @staticmethod
    def _customer_doc(c: Customer) -> dict:
        doc = asdict(c)
        doc["_id"] = doc.pop("id")
        doc["created_at"] = doc["created_at"].isoformat()
        return doc

    def insert_customers(self, rows, session=None):
        from pymongo.errors import BulkWriteError, DuplicateKeyError as MongoDuplicate

        try:
            self.db.customers.insert_many([self._customer_doc(c) for c in rows], session=session)
        except (MongoDuplicate, BulkWriteError) as error:
            details = getattr(error, "details", {}) or {}
            codes = [e.get("code") for e in details.get("writeErrors", [])]
            if isinstance(error, MongoDuplicate) or 11000 in codes:
                raise DuplicateKeyError(str(error)) from error
            raise

    def insert_orders(self, rows):
        docs = []
        for o in rows:
            doc = asdict(o)
            doc["_id"] = doc.pop("id")
            docs.append(doc)
        self.db.orders.insert_many(docs)

    def count(self, table):
        return self.db[table].count_documents({})

    def customer_ids_in(self, city):
        return [d["_id"] for d in self.db.customers.find({"city": city}, {"_id": 1}).sort("_id")]

    def orders_of(self, customer_id):
        pipeline = [
            {"$match": {"customer_id": customer_id}},
            {"$lookup": {"from": "customers", "localField": "customer_id",
                         "foreignField": "_id", "as": "customer"}},
            {"$unwind": "$customer"},
            {"$sort": {"_id": 1}},
            {"$project": {"_id": 1, "name": "$customer.name", "amount_cents": 1}},
        ]
        return [(d["_id"], d["name"], d["amount_cents"]) for d in self.db.orders.aggregate(pipeline)]

    def revenue_by_city(self):
        pipeline = [
            {"$lookup": {"from": "customers", "localField": "customer_id",
                         "foreignField": "_id", "as": "customer"}},
            {"$unwind": "$customer"},
            {"$group": {"_id": "$customer.city", "total": {"$sum": "$amount_cents"}}},
        ]
        return {d["_id"]: int(d["total"]) for d in self.db.orders.aggregate(pipeline)}

    def set_status(self, customer_id, old, new):
        result = self.db.orders.update_many(
            {"customer_id": customer_id, "status": old}, {"$set": {"status": new}}
        )
        return result.modified_count

    def count_status(self, status, customer_id=None):
        query = {"status": status}
        if customer_id is not None:
            query["customer_id"] = customer_id
        return self.db.orders.count_documents(query)

    def insert_customers_then_rollback(self, rows):
        with self.client.start_session() as session:
            session.start_transaction()
            try:
                self.insert_customers(rows, session=session)
            finally:
                session.abort_transaction()


ADAPTERS = {"postgres": PostgresAdapter, "mysql": MySqlAdapter, "mongo": MongoAdapter}


def connect(target: Target) -> DatabaseAdapter:
    """Server-level connection to the given target."""
    return ADAPTERS[target.family](target)
