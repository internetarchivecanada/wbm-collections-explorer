#!/usr/bin/env python3
"""Guard fetch_snapshot.py: a bad, stale or unreachable studio snapshot must
never be written, and a good one must come out in the committed format.
Offline — snapshots are served from file:// URLs.
Run: python3 test_fetch_snapshot.py
"""
import datetime as dt
import io
import json
import os
import pathlib
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "app"))

import core  # noqa: E402
import fetch_snapshot as fs  # noqa: E402

DATA = os.path.join(HERE, "app", "data", "collections.json")
NOW = dt.datetime(2026, 10, 7, 17, 0, tzinfo=dt.timezone.utc)
LIMITS = dict(max_age_hours=48, min_collections=45, min_profiles=40)
FRESH = "2026-10-07T13:57:23+00:00"


def snapshot(generated=FRESH):
    d = json.load(open(DATA))
    d["generated"] = generated
    return d


def rejected(d, needle):
    problems = fs.check(d, NOW, **LIMITS)
    assert any(needle in p for p in problems), f"expected {needle!r} in {problems}"


def run(payload):
    """Serve payload from a file:// URL onto an existing 'ORIGINAL' file; return (rc, text, stdout)."""
    with tempfile.TemporaryDirectory() as tmp:
        src, out = os.path.join(tmp, "snap.json"), os.path.join(tmp, "out.json")
        with open(src, "w") as f:
            f.write(payload if isinstance(payload, str) else json.dumps(payload))
        with open(out, "w") as f:
            f.write("ORIGINAL")
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = fs.main(["--url", pathlib.Path(src).as_uri(), "--out", out, "--backoff", "0"])
        return rc, open(out).read(), buf.getvalue()


def main():
    # check(): the committed dataset is acceptable when fresh
    assert fs.check(snapshot(), NOW, **LIMITS) == [], fs.check(snapshot(), NOW, **LIMITS)

    rejected(snapshot("2026-10-04T13:57:23+00:00"), "older than")
    rejected(snapshot("yesterday"), "unparseable")
    rejected(snapshot("2026-10-07T13:00:00"), "timezone")
    assert fs.check([], NOW, **LIMITS) == ["not a JSON object"]

    d = snapshot()
    d["collections"] = d["collections"][:44]
    rejected(d, "collections, expected")

    d = snapshot()
    for c in d["collections"][39:]:
        c["has_profile"] = False
    rejected(d, "profiled, expected")

    d = snapshot()
    del d["collections"][3]["index_age_days"]    # would silently render every index "Unknown"
    rejected(d, "missing index_age_days")

    d = snapshot()
    d["collections"][3]["has_profile"] = "yes"   # truthy string must not count as profiled
    rejected(d, "has_profile")

    d = snapshot()
    d["collections"][3]["count"] = "12"
    rejected(d, "count")

    d = snapshot()
    d["collections"][3]["title"] = ""
    rejected(d, "title")

    d = snapshot()
    profiled = next(c for c in d["collections"] if c["has_profile"])
    profiled["years"] = None
    rejected(d, "years")

    d = snapshot()
    d["totals"] = {}
    rejected(d, "totals")

    d = snapshot()
    d["collections"][5]["id"] = d["collections"][4]["id"]   # build.py would overwrite c/<id>/
    rejected(d, "duplicate id")

    # fetch(): one transient failure is retried, then the good response is used
    calls = []
    real = fs.urllib.request.urlopen

    def flaky(req, timeout):
        calls.append(req.full_url)
        if len(calls) == 1:
            raise OSError("connection reset by peer")
        return io.BytesIO(json.dumps({"ok": True}).encode())

    fs.urllib.request.urlopen = flaky
    try:
        assert fs.fetch("https://studio.invalid/x.json", 1, 3, 0) == {"ok": True}
    finally:
        fs.urllib.request.urlopen = real
    assert len(calls) == 2, calls

    # main(): a good snapshot is written, in committed format, and still renders
    good = snapshot(dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    for c in good["collections"]:
        c.update(category_label="x", bar=0.5, age_phrase="today", freshness=["current", "Live", ""])
    rc, text, _ = run(good)
    assert rc == 0, rc
    written = json.loads(text)
    assert len(written["collections"]) == len(good["collections"])
    for c in written["collections"]:
        for k in fs.DERIVED:
            assert k not in c, f"{c['id']} kept display key {k}"
        for k in fs.RECORD_KEYS:
            assert k in c, f"{c['id']} lost {k}"
    core.enrich(written)  # the build's own transform must accept it

    # main(): every failure leaves the existing file untouched and exits non-zero
    assert run("{not json")[:2] == (1, "ORIGINAL")
    assert run(snapshot("2020-01-01T00:00:00+00:00"))[:2] == (1, "ORIGINAL")
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.json")
        with open(out, "w") as f:
            f.write("ORIGINAL")
        missing = pathlib.Path(tmp, "absent.json").as_uri()
        with redirect_stdout(io.StringIO()):
            rc = fs.main(["--url", missing, "--out", out, "--backoff", "0"])
        assert rc == 1 and open(out).read() == "ORIGINAL"

    # snapshot text must not be able to inject workflow commands
    evil = snapshot(dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    evil["collections"][0]["id"] = "x\n::error::injected%0A::warning::too"
    del evil["collections"][0]["count"]
    rc, text, stdout = run(evil)
    assert (rc, text) == (1, "ORIGINAL")
    assert stdout.count("\n") == 1 and stdout.startswith("::error::"), repr(stdout)
    assert "%0A::warning::" not in stdout, "a literal %0A in data must be escaped as %250A"

    print("ok — sound snapshots accepted, every bad one refused, existing data never touched")


if __name__ == "__main__":
    main()
