#!/usr/bin/env python3
"""Wayback Collection Search Explorer — a tile view of every collection in the
web.archive.org Collection Search drop-down.

Data is baked by refresh.py into data/collections.json; this process only serves it.
Served under a path prefix by Caddy (X-Forwarded-Prefix), so all links are relative.

The presentation logic lives in core.py, shared with the static builder ../build.py.
"""
import os

from flask import Flask, abort, jsonify, render_template, request  # noqa: F401

import core
from core import DATA_PATH, VERSION, enrich

app = Flask(__name__)


class PrefixMiddleware:
    """Honour X-Forwarded-Prefix so url_for() emits the Caddy-mounted path."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        prefix = environ.get("HTTP_X_FORWARDED_PREFIX", "")
        if prefix:
            environ["SCRIPT_NAME"] = prefix.rstrip("/")
        return self.wsgi_app(environ, start_response)


app.wsgi_app = PrefixMiddleware(app.wsgi_app)

for _name, _fn in core.FILTERS.items():
    app.add_template_filter(_fn, _name)

_cache = {"mtime": None, "data": None}


def load():
    try:
        mtime = os.path.getmtime(DATA_PATH)
    except OSError:
        abort(503, "dataset not built yet — run refresh.py")
    if _cache["mtime"] != mtime:
        _cache["data"] = core.read_data()
        _cache["mtime"] = mtime
    return _cache["data"]


@app.route("/")
def index():
    return render_template("index.html", d=enrich(load()), version=VERSION)


@app.route("/c/<path:cid>")
def detail(cid):
    data = enrich(load())
    match = next((c for c in data["collections"] if c["id"] == cid), None)
    if not match:
        abort(404)
    return render_template("detail.html", d=data, c=match, version=VERSION)


@app.route("/api/collections.json")
def api():
    return jsonify(load())


@app.route("/healthz")
def healthz():
    d = load()
    return jsonify(ok=True, version=VERSION, generated=d["generated"],
                   collections=len(d["collections"]))


@app.errorhandler(404)
def nf(_e):
    try:
        data = load()
    except Exception:  # noqa: BLE001
        data = {"generated": "", "collections": []}
    return render_template("404.html", d=data, version=VERSION), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 8330)), debug=False)
