"""Database servers under test: one matrix per family, one column per version.

Every server runs in its own Docker container (see docker-compose.yml, profile
``databases``) and is published on its own host port.

Environment variables:
    DB_HOST      host where the containers are published (default: localhost)
    DB_TARGETS   comma-separated subset to test, e.g. "postgres:16,mysql:8.0"
    DB_REQUIRED  "1" to fail (instead of skip) when a server is unreachable
"""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    family: str   # postgres | mysql | mongo
    version: str  # image tag, also the matrix column
    port: int

    @property
    def id(self) -> str:
        return f"{self.family}:{self.version}"

    @property
    def host(self) -> str:
        return os.getenv("DB_HOST", "localhost")


ALL_TARGETS = [
    Target("postgres", "14", 5414),
    Target("postgres", "15", 5415),
    Target("postgres", "16", 5416),
    Target("postgres", "17", 5417),
    Target("mysql", "8.0", 3380),
    Target("mysql", "8.4", 3384),
    Target("mongo", "6.0", 27060),
    Target("mongo", "7.0", 27070),
    Target("mongo", "8.0", 27080),
]

# Same credentials as in docker-compose.yml (test containers only).
USER = {"postgres": "qa", "mysql": "root"}
PASSWORD = "qa_password"


def selected_targets() -> list[Target]:
    wanted = os.getenv("DB_TARGETS", "").replace(" ", "")
    if not wanted:
        return ALL_TARGETS
    ids = set(wanted.split(","))
    return [t for t in ALL_TARGETS if t.id in ids or t.family in ids]


DB_REQUIRED = os.getenv("DB_REQUIRED", "0") == "1"
