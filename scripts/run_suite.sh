#!/usr/bin/env bash
# Run the whole suite, then build the matrices (and post them to Slack when
# SLACK_WEBHOOK_URL is set).
#
#   ./scripts/run_suite.sh                       # mode from QA_MODE (default: local)
#   QA_MODE=remote ./scripts/run_suite.sh        # against the hosted apps
#   BROWSERS="chromium firefox" ./scripts/run_suite.sh
set -uo pipefail
cd "$(dirname "$0")/.."

PY="${PYTHON:-python3}"
export QA_MODE="${QA_MODE:-local}"
browsers=()
for b in ${BROWSERS:-chromium}; do browsers+=(--browser "$b"); done

echo "Running QA suite in ${QA_MODE} mode (${BROWSERS:-chromium})"
"$PY" -m pytest "${browsers[@]}" "$@"
pytest_status=$?

slack_flag=()
[[ -n "${SLACK_WEBHOOK_URL:-}" ]] && slack_flag=(--slack)
"$PY" -m reporting.build_report "${slack_flag[@]}"

exit "$pytest_status"
