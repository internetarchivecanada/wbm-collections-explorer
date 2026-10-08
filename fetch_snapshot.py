#!/usr/bin/env python3
"""Fetch the dataset the studio deployment publishes, for the serverless build.

The studio host re-harvests web.archive.org every night from inside the
Internet Archive network. Harvesting again from a GitHub runner is slow and
unreliable: runner IPs are refused or throttled, and from 2026-10-01 the
harvest overran the job timeout every night, so nothing was deployed. This
fetches the studio's /api/collections.json instead, checks it, and writes it
to app/data/collections.json.

It fails closed. If the fetch or any check fails, nothing is written and the
exit status is 1, so CI stops before deploying and GitHub Pages keeps the last
good site. Falling back to the committed dataset would be worse: it is older
than whatever Pages is already serving.

    python3 fetch_snapshot.py                 # studio -> app/data/collections.json
    python3 fetch_snapshot.py --url URL --out PATH
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_URL = "https://wayback-labs.sf.archive.org/collections/api/collections.json"
DEFAULT_OUT = os.path.join(HERE, "app", "data", "collections.json")
UA = "wayback-collections-explorer-ci/1.0 (+mark@archive.org)"

REQUIRED_TOP = ("generated", "collections", "categories", "category_order", "totals", "unlisted")
REQUIRED_TOTALS = ("collections", "documents", "global_indexes")
# Every field refresh.py writes per collection; the templates read nearly all of them.
RECORD_KEYS = (
    "id", "title", "blurb", "category", "kind", "count", "share", "indexes",
    "index_updated", "index_age_days", "api_title", "api_description", "search_url",
    "item_url", "item", "years", "year_min", "year_max", "years_capped",
    "top_domains", "domain_count_capped", "top_languages", "language_count_capped",
    "tlds", "dead_known", "dead_share", "dead_sampled", "seed_known", "seed_count",
    "has_profile",
)
# Display fields the server's enrich() adds to its in-memory copy. build.py
# recomputes them, so they stay out of the committed-format dataset.
DERIVED = ("category_label", "bar", "age_phrase", "freshness")


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _record_problems(c):
    if not isinstance(c, dict):
        return ["a collection record is not an object"]
    cid = c.get("id") if isinstance(c.get("id"), str) else "?"
    missing = [k for k in RECORD_KEYS if k not in c]
    if missing:
        return [f"{cid} is missing {', '.join(missing)}"]
    bad = [k for k in ("id", "title", "category", "kind")
           if not isinstance(c[k], str) or not c[k]]
    if not _is_int(c["count"]) or c["count"] < 0:
        bad.append("count")
    if not isinstance(c["share"], (int, float)) or isinstance(c["share"], bool):
        bad.append("share")
    if not isinstance(c["has_profile"], bool):
        bad.append("has_profile")
    if c["index_age_days"] is not None and not _is_int(c["index_age_days"]):
        bad.append("index_age_days")
    if c["has_profile"] is True:
        if not isinstance(c["years"], dict):
            bad.append("years")
        bad += [k for k in ("top_domains", "top_languages", "tlds")
                if not isinstance(c[k], list)]
    return [f"{cid} has a bad {', '.join(bad)}"] if bad else []


def check(data, now, max_age_hours, min_collections, min_profiles):
    """Reasons the snapshot is unusable; an empty list means it is fine."""
    if not isinstance(data, dict):
        return ["not a JSON object"]
    problems = [f"missing top-level key {k!r}" for k in REQUIRED_TOP if k not in data]
    if problems:
        return problems
    if not isinstance(data["totals"], dict) or any(k not in data["totals"] for k in REQUIRED_TOTALS):
        problems.append(f"totals must have {', '.join(REQUIRED_TOTALS)}")

    cols = data["collections"]
    if not isinstance(cols, list) or len(cols) < min_collections:
        n = len(cols) if isinstance(cols, list) else "no"
        return problems + [f"{n} collections, expected at least {min_collections}"]
    for c in cols:
        problems += _record_problems(c)
    ids = [c["id"] for c in cols if isinstance(c, dict) and isinstance(c.get("id"), str)]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        problems.append(f"duplicate id {', '.join(dupes)}")

    profiled = sum(1 for c in cols if isinstance(c, dict) and c.get("has_profile") is True)
    if profiled < min_profiles:
        problems.append(f"{profiled} collections profiled, expected at least {min_profiles}")

    try:
        generated = dt.datetime.fromisoformat(data["generated"])
    except (TypeError, ValueError):
        problems.append(f"unparseable generated {data['generated']!r}")
    else:
        if generated.tzinfo is None:
            problems.append(f"generated {data['generated']!r} has no timezone")
        elif now - generated > dt.timedelta(hours=max_age_hours):
            problems.append(f"snapshot generated {data['generated']} is older than {max_age_hours:g}h")
    return problems


def strip_derived(data):
    for c in data["collections"]:
        for k in DERIVED:
            c.pop(k, None)
    return data


def write_atomic(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, path)


def workflow_error(msg):
    """One GitHub ::error:: line. Escape so snapshot text cannot start a new command."""
    msg = str(msg).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error::{msg}")


def fetch(url, timeout, tries, backoff):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # noqa: BLE001 - reported once, after the last try
            last = e
            if attempt < tries - 1:
                time.sleep(backoff * (attempt + 1))
    raise last


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=float, default=30, help="per socket operation, seconds")
    ap.add_argument("--tries", type=int, default=3)
    ap.add_argument("--backoff", type=float, default=10, help="seconds, grows per retry")
    ap.add_argument("--max-age-hours", type=float, default=48)
    ap.add_argument("--min-collections", type=int, default=45)
    ap.add_argument("--min-profiles", type=int, default=40)
    args = ap.parse_args(argv)

    try:
        data = fetch(args.url, args.timeout, args.tries, args.backoff)
    except Exception as e:  # noqa: BLE001
        workflow_error(f"studio snapshot unavailable after {args.tries} tries: {e}")
        return 1

    problems = check(data, dt.datetime.now(dt.timezone.utc), args.max_age_hours,
                     args.min_collections, args.min_profiles)
    if problems:
        workflow_error("studio snapshot rejected: " + "; ".join(problems[:5]))
        return 1

    write_atomic(args.out, strip_derived(data))
    profiled = sum(1 for c in data["collections"] if c["has_profile"])
    print(f"wrote {args.out}: {len(data['collections'])} collections, {profiled} profiled, "
          f"generated {data['generated']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
