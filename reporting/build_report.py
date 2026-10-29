"""Merge run results into matrices: one matrix per suite, tests as rows,
variants as columns.

    python -m reporting.build_report            # HTML + Markdown in reports/
    python -m reporting.build_report --slack    # ...and post to Slack
"""

import argparse
import html
import json
import os
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import config
from reporting import slack

ICONS = {"passed": "✅", "failed": "❌", "error": "⚠️", "skipped": "⏭️", None: "·"}
SHORT = {"passed": "✔", "failed": "✘", "error": "!", "skipped": "-", None: "·"}


@dataclass
class Matrix:
    title: str
    mode: str
    rows: list = field(default_factory=list)
    columns: list = field(default_factory=list)
    cells: dict = field(default_factory=dict)  # (row, column) -> result dict

    def add(self, result):
        row, col = result["row"], result["column"]
        if row not in self.rows:
            self.rows.append(row)
        if col not in self.columns:
            self.columns.append(col)
        self.cells[(row, col)] = result

    @property
    def counts(self) -> Counter:
        return Counter(r["status"] for r in self.cells.values())


def load_runs(results_dir: Path) -> list[dict]:
    runs = [json.loads(p.read_text()) for p in sorted(results_dir.glob("results-*.json"))]
    return sorted(runs, key=lambda run: run["started"])  # later runs overwrite earlier cells


def build(runs: list[dict]):
    matrices: dict[tuple, Matrix] = {}
    standalone: dict[str, dict] = {}
    for run in runs:
        for result in run["results"]:
            result = {**result, "mode": run["mode"]}
            if result["row"] is None:
                standalone[f'{run["mode"]}::{result["nodeid"]}'] = result
                continue
            key = (result["matrix"], run["mode"])
            matrices.setdefault(key, Matrix(result["matrix"], run["mode"])).add(result)
    return list(matrices.values()), list(standalone.values())


def column_label(column) -> str:
    return str(column).removesuffix("_user") if column else "—"


# --- Markdown (GitHub job summary) ------------------------------------------

def to_markdown(matrices, standalone, totals) -> str:
    lines = [f"# Nightly QA matrix\n", summary_line(totals), ""]
    for m in matrices:
        lines += [f"## {m.title} ({m.mode})", ""]
        lines.append("| Test | " + " | ".join(column_label(c) for c in m.columns) + " |")
        lines.append("|---|" + "---|" * len(m.columns))
        for row in m.rows:
            cells = [ICONS[m.cells.get((row, c), {}).get("status")] for c in m.columns]
            lines.append(f"| {row} | " + " | ".join(cells) + " |")
        lines.append("")
    if standalone:
        lines += ["## Standalone checks", "", "| Check | Suite | Mode | Result |", "|---|---|---|---|"]
        for r in standalone:
            lines.append(f'| {r["test"]} | {r["matrix"].split(" · ")[0]} | {r["mode"]} | {ICONS[r["status"]]} |')
        lines.append("")
    failures = [r for m in matrices for r in m.cells.values() if r["status"] in ("failed", "error")]
    failures += [r for r in standalone if r["status"] in ("failed", "error")]
    if failures:
        lines += ["## Failure details", ""]
        for r in failures:
            where = f'{r["row"]} / {column_label(r["column"])}' if r["row"] else r["test"]
            lines.append(f'- **{where}** ({r["matrix"]}, {r["mode"]}): {r["message"] or r["status"]}')
    return "\n".join(lines) + "\n"


def summary_line(totals: Counter) -> str:
    total = sum(totals.values())
    return (f"**{totals['passed']}/{total} passed** · {totals['failed']} failed · "
            f"{totals['error']} errors · {totals['skipped']} skipped")


# --- HTML ---------------------------------------------------------------------

def to_html(matrices, standalone, totals, runs) -> str:
    esc = html.escape

    def cell(result):
        status = result.get("status") if result else None
        tip = esc(result.get("message", "")) if result else ""
        dur = f'{result["duration"]:.1f}s' if result else ""
        return (f'<td class="c {status or "none"}" title="{tip}">'
                f'<span>{SHORT[status]}</span><small>{dur}</small></td>')

    sections = []
    for m in matrices:
        head = "".join(f"<th>{esc(column_label(c))}</th>" for c in m.columns)
        body = "".join(
            f"<tr><th class='row'>{esc(row)}</th>"
            + "".join(cell(m.cells.get((row, c))) for c in m.columns) + "</tr>"
            for row in m.rows
        )
        c = m.counts
        sections.append(
            f"<section><h2>{esc(m.title)} <em>{esc(m.mode)}</em></h2>"
            f"<p class='meta'>{c['passed']} passed · {c['failed']} failed · {c['error']} errors</p>"
            f"<div class='scroll'><table><thead><tr><th></th>{head}</tr></thead>"
            f"<tbody>{body}</tbody></table></div></section>"
        )
    if standalone:
        rows = "".join(
            f"<tr><th class='row'>{esc(r['test'])}</th><td>{esc(r['matrix'].split(' · ')[0])}</td>"
            f"<td>{esc(r['mode'])}</td>{cell(r)}</tr>" for r in standalone
        )
        sections.append("<section><h2>Standalone checks</h2><div class='scroll'><table>"
                        "<thead><tr><th></th><th>Suite</th><th>Mode</th><th>Result</th></tr></thead>"
                        f"<tbody>{rows}</tbody></table></div></section>")
    failures = [r for m in matrices for r in m.cells.values() if r["status"] in ("failed", "error")]
    failures += [r for r in standalone if r["status"] in ("failed", "error")]
    if failures:
        items = "".join(
            f"<li><b>{esc(r['row'] + ' / ' + column_label(r['column']) if r['row'] else r['test'])}</b> "
            f"<span class='meta'>{esc(r['matrix'])} · {esc(r['mode'])}</span><br>"
            f"<code>{esc(r['message'] or r['status'])}</code></li>" for r in failures
        )
        sections.append(f"<section><h2>Failure details</h2><ul class='fail'>{items}</ul></section>")

    when = runs[-1]["finished"].replace("T", " ").replace("+00:00", "") + " UTC" if runs else ""
    total = sum(totals.values())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>QA Results Matrix</title>
<style>
:root {{ --bg:#f7f8fa; --card:#fff; --ink:#1d2433; --muted:#667085; --line:#e4e7ec;
  --pass:#e3f6ea; --pass-ink:#137a3c; --fail:#fde8e8; --fail-ink:#b42318;
  --err:#fff4e0; --err-ink:#b54708; --skip:#eef0f4; --skip-ink:#667085; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#11141a; --card:#191d25; --ink:#e7eaf0;
  --muted:#98a2b3; --line:#2a303b; --pass:#123524; --pass-ink:#5fd38d; --fail:#3d1716;
  --fail-ink:#ff8a80; --err:#3a2a10; --err-ink:#fdb022; --skip:#232833; --skip-ink:#98a2b3; }} }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink);
  font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif; padding:24px 16px }}
main {{ max-width:1000px; margin:0 auto }}
h1 {{ font-size:22px; margin:0 0 4px }} h2 {{ font-size:16px; margin:0 0 4px }}
h2 em {{ font-style:normal; font-weight:500; color:var(--muted); font-size:13px;
  border:1px solid var(--line); border-radius:99px; padding:1px 8px; margin-left:6px }}
.meta {{ color:var(--muted); font-size:13px; margin:0 0 12px }}
.total {{ display:flex; gap:20px; flex-wrap:wrap; margin:12px 0 24px }}
.total div {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 16px }}
.total b {{ display:block; font-size:22px }}
section {{ background:var(--card); border:1px solid var(--line); border-radius:12px;
  padding:16px; margin-bottom:16px }}
.scroll {{ overflow-x:auto }}
table {{ border-collapse:separate; border-spacing:4px; width:100% }}
th {{ font-weight:600; font-size:12px; color:var(--muted); text-align:center; padding:4px 6px }}
th.row {{ text-align:left; color:var(--ink); font-size:13px; white-space:nowrap }}
td {{ text-align:center; border-radius:6px; padding:6px 4px; min-width:72px }}
td.c span {{ font-weight:700; font-size:15px }} td.c small {{ display:block; font-size:11px; opacity:.7 }}
.passed {{ background:var(--pass); color:var(--pass-ink) }} .failed {{ background:var(--fail); color:var(--fail-ink) }}
.error {{ background:var(--err); color:var(--err-ink) }} .skipped,.none {{ background:var(--skip); color:var(--skip-ink) }}
ul.fail {{ padding-left:18px; margin:0 }} ul.fail li {{ margin-bottom:10px }}
code {{ font-size:12px; color:var(--fail-ink); word-break:break-word }}
</style></head><body><main>
<h1>QA Results Matrix</h1>
<p class="meta">Last run: {esc(when)} · hover a cell to see the failure message</p>
<div class="total"><div><b>{totals['passed']}/{total}</b>passed</div>
<div><b>{totals['failed']}</b>failed</div><div><b>{totals['error']}</b>errors</div>
<div><b>{totals['skipped']}</b>skipped</div></div>
{''.join(sections)}
</main></body></html>
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default=config.RESULTS_DIR)
    parser.add_argument("--out", default="reports")
    parser.add_argument("--slack", action="store_true", help="post the matrices to Slack")
    parser.add_argument("--fail-on-failure", action="store_true",
                        help="exit 1 when any test failed or errored")
    args = parser.parse_args(argv)

    runs = load_runs(Path(args.results))
    if not runs:
        print(f"No results found in {args.results}", file=sys.stderr)
        return 1
    matrices, standalone = build(runs)
    totals = Counter(r["status"] for m in matrices for r in m.cells.values())
    totals.update(r["status"] for r in standalone)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    markdown = to_markdown(matrices, standalone, totals)
    (out / "matrix.md").write_text(markdown)
    (out / "matrix.html").write_text(to_html(matrices, standalone, totals, runs))
    print(markdown)

    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_file:
        with open(summary_file, "a") as fh:
            fh.write(markdown)

    if args.slack:
        slack.post(matrices, standalone, totals, runs[-1].get("run_url", ""))

    return 1 if args.fail_on_failure and (totals["failed"] or totals["error"]) else 0


if __name__ == "__main__":
    sys.exit(main())
