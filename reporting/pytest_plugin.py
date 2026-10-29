"""Pytest plugin that records each test as a cell of a results matrix.

A test marked ``@pytest.mark.matrix("Checkout")`` becomes the row "Checkout";
its column is the parametrized variant (user profile for UI tests, dataset
for API tests); its matrix is the suite (one per browser for UI). Unmarked
tests are kept as standalone checks. One JSON file is written per run and
``reporting.build_report`` merges them into the final matrices.
"""

import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

import pytest

import config as settings

_SEVERITY = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "matrix(row): report this test as a row of the results matrix"
    )
    config._matrix_results = {}
    config._matrix_started = datetime.now(timezone.utc)


def _locate(item):
    """Return (matrix, column) for a test item."""
    params = getattr(item, "callspec", None)
    params = params.params if params else {}
    if "tests/ui" in item.nodeid.replace("\\", "/"):
        browser = item.funcargs.get("browser_name") or params.get("browser_name", "chromium")
        return f"UI · {browser}", params.get("user")
    dataset = params.get("dataset")
    return "API · restful-booker", dataset


def _short_message(report) -> str:
    text = getattr(report, "longreprtext", "") or ""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("E ")]
    message = lines[0][1:].strip() if lines else (text.strip().splitlines() or [""])[-1]
    return message[:300]


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if report.passed:
        status = "passed"
    elif report.skipped:
        status = "skipped"
    else:
        status = "failed" if report.when == "call" else "error"
    if report.when != "call" and status == "passed":
        status = None  # setup/teardown success says nothing new

    results = item.config._matrix_results
    entry = results.get(item.nodeid)
    if entry is None:
        marker = item.get_closest_marker("matrix")
        matrix, column = _locate(item)
        entry = results[item.nodeid] = {
            "nodeid": item.nodeid,
            "test": item.originalname or item.name,
            "matrix": matrix if marker else f"{matrix.split(' · ')[0]} · standalone",
            "row": marker.args[0] if marker else None,
            "column": column if marker else None,
            "status": "passed",
            "message": "",
            "duration": 0.0,
        }
    entry["duration"] = round(entry["duration"] + report.duration, 3)
    if status and _SEVERITY[status] > _SEVERITY[entry["status"]]:
        entry["status"] = status
        entry["message"] = _short_message(report) if status != "skipped" else str(report.longrepr[-1])


def pytest_sessionfinish(session):
    results = list(getattr(session.config, "_matrix_results", {}).values())
    if not results:
        return
    out_dir = Path(settings.RESULTS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = session.config._matrix_started
    payload = {
        "mode": settings.MODE,
        "targets": {"ui": settings.SAUCE_URL, "api": settings.BOOKER_URL},
        "started": started.isoformat(timespec="seconds"),
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "host": platform.node(),
        "run_url": os.getenv("RUN_URL", ""),
        "results": results,
    }
    name = f"results-{settings.MODE}-{started:%Y%m%dT%H%M%S}-{os.getpid()}.json"
    (out_dir / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False))
