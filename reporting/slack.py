"""Send the matrices to a Slack channel through an incoming webhook.

Slack has no table formatting, so each matrix is drawn as a fixed-width grid
inside a code block:  ✔ passed · ✘ failed · ! error · - skipped
"""

import os

import requests

SHORT = {"passed": "✔", "failed": "✘", "error": "!", "skipped": "-", None: "·"}


def _grid(matrix) -> str:
    labels = [str(c).removesuffix("_user") for c in matrix.columns]
    first = max(len(r) for r in matrix.rows)
    widths = [max(len(label), 3) for label in labels]
    header = " " * first + "  " + "  ".join(l.center(w) for l, w in zip(labels, widths))
    lines = [header]
    for row in matrix.rows:
        cells = [
            SHORT[matrix.cells.get((row, c), {}).get("status")].center(w)
            for c, w in zip(matrix.columns, widths)
        ]
        lines.append(row.ljust(first) + "  " + "  ".join(cells))
    return "\n".join(lines)


def build_message(matrices, standalone, totals, run_url: str = "") -> dict:
    total = sum(totals.values())
    failed = totals["failed"] + totals["error"]
    status = ":white_check_mark: All green" if not failed else f":x: {failed} failing"
    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": "Nightly QA matrix"}},
        {"type": "section", "text": {"type": "mrkdwn",
                                     "text": f"*{status}* · {totals['passed']}/{total} passed"}},
    ]
    for m in matrices:
        blocks.append({"type": "section", "text": {
            "type": "mrkdwn", "text": f"*{m.title}* ({m.mode})\n```\n{_grid(m)}\n```"}})
    broken = [r["test"] for r in standalone if r["status"] in ("failed", "error")]
    if broken:
        blocks.append({"type": "section", "text": {
            "type": "mrkdwn", "text": "*Standalone checks failing:* " + ", ".join(broken)}})
    if run_url:
        blocks.append({"type": "context", "elements": [
            {"type": "mrkdwn", "text": f"<{run_url}|Full report and logs>"}]})
    return {"text": f"Nightly QA: {totals['passed']}/{total} passed", "blocks": blocks}


def post(matrices, standalone, totals, run_url: str = "") -> None:
    webhook = os.getenv("SLACK_WEBHOOK_URL")
    message = build_message(matrices, standalone, totals, run_url)
    if not webhook:
        print("SLACK_WEBHOOK_URL not set: Slack message not sent. Preview:\n")
        for block in message["blocks"]:
            print(block.get("text", {}).get("text", ""))
        return
    response = requests.post(webhook, json=message, timeout=15)
    response.raise_for_status()
    print("Matrix posted to Slack.")
