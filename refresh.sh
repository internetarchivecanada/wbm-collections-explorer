#!/bin/bash
# Re-harvest the Wayback collection roster + per-collection profiles.
# The two biggest indexes (pdf, telegram) usually 504 on the aggregation call;
# refresh.py keeps the previous profile when a fetch fails, so a partial run is safe.
cd /opt/services/collections/app || exit 1
echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') refresh start"
./venv/bin/python refresh.py --sleep 2
echo "=== $(date -u '+%Y-%m-%dT%H:%M:%SZ') refresh done (exit $?)"
