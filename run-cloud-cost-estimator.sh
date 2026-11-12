#!/bin/bash
# Emails the monthly cost report. Safe to run from cron (uses absolute paths).
set -euo pipefail
cd "$(dirname "$0")/backend"
UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
"$UV" run --frozen cost-tracker report --email
