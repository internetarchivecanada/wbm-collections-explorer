#!/bin/bash
# collections — Wayback Collection Search Explorer. Launched by launchd (KeepAlive).
# Listens on 127.0.0.1:$PORT; Caddy reverse-proxies /collections/* to it.
cd /opt/services/collections/app || exit 1
export PORT="${PORT:-8331}"
exec ./venv/bin/python app.py
