#!/usr/bin/env python3
"""Harvest every Wayback Machine Collection Search collection into data/collections.json.

Sources (all public, all on web.archive.org):
  1. /__wb/search/collectioninfo?collection=all
       -> the authoritative roster: one entry per (collection, index type) with
          count, last_updated, boilerplate description, archive.org item URL.
          This is what fills the drop-down on https://web.archive.org/collection-search/
  2. /__wb/search/waybacksearch?q=*:*&size=0&collection=<id>
       -> a whole-collection profile: capture-year histogram, top domains,
          top languages, TLDs, seed/dead-link splits.
          The two largest indexes (pdf, telegram) time out server-side; those
          collections simply get no profile and the UI degrades gracefully.
  3. https://archive.org/metadata/<item>/metadata
       -> curator, public date and description for the 13 collections that name
          an archive.org item.

Run:  ./venv/bin/python refresh.py            (writes data/collections.json)
      ./venv/bin/python refresh.py --cached   (reuse cache/, no network)
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
DATA = os.path.join(HERE, "data")
WB = "https://web.archive.org"
UA = "wayback-collections-explorer/1.0 (+mark@archive.org)"

sys.path.insert(0, HERE)
from curation import CATEGORIES, CATEGORY_ORDER, CURATION, UNLISTED_NOTE  # noqa: E402


def fetch(url, timeout=300, tries=3, pause=8):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001 - 502/504 on the big indexes is normal
            last = e
            if attempt < tries - 1:
                time.sleep(pause)
    print(f"  ! {url} -> {last}", file=sys.stderr)
    return None


def cached(name, url, use_cache, **kw):
    path = os.path.join(CACHE, name + ".json")
    if use_cache and os.path.exists(path):
        try:
            return json.load(open(path))
        except Exception:  # noqa: BLE001
            pass
    got = fetch(url, **kw)
    if got is not None:
        os.makedirs(CACHE, exist_ok=True)
        json.dump(got, open(path, "w"))
    elif os.path.exists(path):
        try:
            return json.load(open(path))   # keep the last good profile
        except Exception:  # noqa: BLE001
            pass
    return got


def rel_age(datestr):
    """'2026-08-22' or ISO timestamp -> (iso_date, days_old)."""
    if not datestr:
        return None, None
    d = datestr[:10]
    try:
        then = dt.date.fromisoformat(d)
    except ValueError:
        return d, None
    return d, (dt.date.today() - then).days


# Everything in a record that comes from the aggregation call, as opposed to the
# roster (count, index_updated) or curation (title, blurb). These are the fields
# a refused or timed-out profile fetch would otherwise blank out.
PROFILE_KEYS = (
    "years", "year_min", "year_max", "years_capped",
    "top_domains", "domain_count_capped", "top_languages", "language_count_capped",
    "tlds", "dead_known", "dead_share", "dead_sampled", "seed_known", "seed_count",
    "has_profile",
)


def carry_forward(out, prev_path):
    """Keep the last good profile for any collection whose fetch just failed.

    The aggregation endpoint 504s on the two largest indexes and refuses
    outright from some IPs (GitHub runners, notably), so a run that harvests
    fewer profiles than the last one is normal. Without this a bad run would
    overwrite good data with blanks; with it, a run can only improve or hold.

    Counts and index dates come from the roster, a single request, so they stay
    fresh either way. `profile_asof` records when a carried-over profile was
    actually measured.
    """
    try:
        with open(prev_path) as f:
            prev = json.load(f)
    except (OSError, ValueError):
        return 0
    was = {c["id"]: c for c in prev.get("collections", [])}
    asof = (prev.get("generated") or "")[:10]
    kept = 0
    for c in out:
        if c["has_profile"]:
            continue
        old_c = was.get(c["id"])
        if not old_c or not old_c.get("has_profile"):
            continue
        for k in PROFILE_KEYS:
            if k in old_c:
                c[k] = old_c[k]
        c["profile_asof"] = old_c.get("profile_asof") or asof
        kept += 1
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cached", action="store_true", help="reuse cache/, no network")
    ap.add_argument("--sleep", type=float, default=2.0)
    args = ap.parse_args()
    uc = args.cached

    roster = cached("collectioninfo_all", f"{WB}/__wb/search/collectioninfo?collection=all", uc, timeout=120)
    if not roster:
        sys.exit("could not fetch the collection roster")

    # --- 1. fold the (collection, index-type) rows into one record per collection
    listed, globals_, unlisted = {}, {}, {}
    for key, row in roster.items():
        idx = key.rsplit("-search-", 1)[1] if "-search-" in key else None
        cid = row.get("collection")
        if not cid:
            # rows with no `collection` field are either the global wayback-* indexes
            # or collections that exist but are absent from the public drop-down
            base = key.rsplit("-search-", 1)[0] if idx else key
            bucket = globals_ if base.startswith("wayback") else unlisted
            b = bucket.setdefault(base, {"count": 0, "by_index": {}})
            b["by_index"][idx or "all"] = int(row["count"])
            b["count"] = max(b["count"], int(row["count"]))
            continue
        r = listed.setdefault(cid, {
            "id": cid, "api_title": row.get("title", cid), "item_url": row.get("url") or "",
            "api_description": row.get("description", ""), "count": int(row["count"]),
            "last_updated": row.get("last_updated", ""), "indexes": [],
        })
        r["indexes"].append(idx or "?")
        r["count"] = max(r["count"], int(row["count"]))
    for r in listed.values():
        r["indexes"] = sorted(set(r["indexes"]))

    print(f"roster: {len(listed)} listed, {len(unlisted)} unlisted, {len(globals_)} global indexes")

    # --- 2. per-collection profile from the search aggregations
    for i, (cid, r) in enumerate(sorted(listed.items()), 1):
        q = urllib.parse.quote(cid)
        prof = cached(
            "agg_" + cid.replace("/", "_"),
            f"{WB}/__wb/search/waybacksearch?q=*%3A*&size=0&page=1&filetype=&collection={q}",
            uc, timeout=300, tries=2, pause=15,
        )
        agg = prof.get("aggregations", {}) if isinstance(prof, dict) else {}
        r["profile"] = {
            "years": {k: v for k, v in sorted(agg.get("first_captured_year", {}).items())},
            "domains": agg.get("domains", {}),
            "languages": agg.get("languages", {}),
            "tlds": agg.get("tlds", {}),
            "publication_date": agg.get("publication_date", {}),
            "is_seed": agg.get("is_seed", {}),
            "is_dead": agg.get("is_dead", {}),
        } if agg else None
        print(f"  [{i:2}/{len(listed)}] {cid:<34} {'profile' if agg else 'NO PROFILE'}")
        if not uc:
            time.sleep(args.sleep)

    # --- 3. archive.org item metadata for the collections that name one
    for cid, r in sorted(listed.items()):
        url = r["item_url"]
        r["item"] = None
        if not url or "/details/" not in url:
            continue
        item_id = url.rstrip("/").rsplit("/details/", 1)[1]
        md = cached("ia_" + item_id, f"https://archive.org/metadata/{item_id}/metadata", uc, timeout=60, tries=2)
        res = (md or {}).get("result") or {}
        if res:
            r["item"] = {
                "id": item_id,
                "title": res.get("title", ""),
                "curator": (res.get("uploader") or "").split("@")[0],
                "public_date": (res.get("publicdate") or "")[:10],
                "subject": res.get("subject", ""),
            }
        if not uc:
            time.sleep(0.5)

    # --- 4. merge with curation and derive the display fields
    out = []
    total = sum(r["count"] for r in listed.values())
    for cid, r in listed.items():
        cur = CURATION.get(cid, {})
        prof = r.get("profile") or {}
        years = prof.get("years") or {}
        dead = prof.get("is_dead") or {}
        seed = prof.get("is_seed") or {}
        d_yes, d_no = int(dead.get("true", 0) or 0), int(dead.get("false", 0) or 0)
        d_tot = d_yes + d_no
        langs = prof.get("languages") or {}
        doms = prof.get("domains") or {}
        iso, age = rel_age(r["last_updated"])

        out.append({
            "id": cid,
            "title": cur.get("title") or r["api_title"],
            "blurb": cur.get("blurb", ""),
            "category": cur.get("category", "topic"),
            "kind": cur.get("kind", "documents"),
            "count": r["count"],
            "share": r["count"] / total if total else 0,
            "indexes": r["indexes"],
            "index_updated": iso,
            "index_age_days": age,
            "api_title": r["api_title"],
            "api_description": r["api_description"],
            "search_url": f"{WB}/collection-search/{urllib.parse.quote(cid)}",
            "item_url": r["item_url"],
            "item": r.get("item"),
            "years": years,
            "year_min": min(years) if years else None,
            "year_max": max(years) if years else None,
            "years_capped": len(years) >= 17,
            "top_domains": list(doms.items())[:6],
            "domain_count_capped": len(doms) >= 17,
            "top_languages": list(langs.items())[:6],
            "language_count_capped": len(langs) >= 17,
            "tlds": list((prof.get("tlds") or {}).items())[:6],
            "dead_known": d_tot > 0,
            "dead_share": (d_yes / d_tot) if d_tot else None,
            "dead_sampled": d_tot,
            "seed_known": bool(seed),
            "seed_count": int(seed.get("true", 0) or 0) if seed else None,
            "has_profile": bool(r.get("profile")),
        })

    out.sort(key=lambda x: -x["count"])
    kept = carry_forward(out, os.path.join(DATA, "collections.json"))

    payload = {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source": f"{WB}/collection-search/",
        "collections": out,
        "categories": CATEGORIES,
        "category_order": CATEGORY_ORDER,
        "totals": {
            "collections": len(out),
            "documents": total,
            "with_profile": sum(1 for c in out if c["has_profile"]),
            "global_indexes": {k: v["by_index"] for k, v in sorted(globals_.items())},
        },
        "unlisted": [
            {"id": k, "count": v["count"], "note": UNLISTED_NOTE.get(k, "")}
            for k, v in sorted(unlisted.items(), key=lambda x: -x[1]["count"])
        ],
    }
    os.makedirs(DATA, exist_ok=True)
    tmp = os.path.join(DATA, "collections.json.tmp")
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=1)
    os.replace(tmp, os.path.join(DATA, "collections.json"))
    print(f"\nwrote data/collections.json — {len(out)} collections, {total:,} documents, "
          f"{payload['totals']['with_profile']} with profiles"
          + (f" ({kept} carried over from the previous run)" if kept else ""))


if __name__ == "__main__":
    main()
