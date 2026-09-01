#!/usr/bin/env python3
"""Guard the one piece of refresh.py that a bad harvest can silently break.

The aggregation endpoint 504s on the largest indexes and refuses outright from
some IPs — a GitHub runner saw 12 of 49 refused. Without carry_forward, such a
run overwrites good profiles with blanks and the published data gets worse every
night. Run: python3 test_refresh.py
"""
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "app"))

from refresh import PROFILE_KEYS, carry_forward  # noqa: E402

DATA = os.path.join(HERE, "app", "data", "collections.json")


def blank(record):
    for k in PROFILE_KEYS:
        record[k] = {} if k == "years" else (False if k == "has_profile" else None)


def main():
    prev = json.load(open(DATA))
    by_id = {c["id"]: c for c in prev["collections"]}
    had = [c["id"] for c in prev["collections"] if c["has_profile"]]
    assert had, "fixture has no profiled collections"

    out = copy.deepcopy(prev["collections"])
    failed = set(had[:12])
    for c in out:
        if c["id"] in failed:
            blank(c)

    kept = carry_forward(out, DATA)
    assert kept == len(failed), f"carried {kept}, expected {len(failed)}"

    now = {c["id"] for c in out if c["has_profile"]}
    assert now == set(had), "carry_forward changed which collections have profiles"

    for cid in failed:
        got = next(c for c in out if c["id"] == cid)
        for k in PROFILE_KEYS:
            assert got[k] == by_id[cid][k], f"{cid}.{k} not restored"
        assert got.get("profile_asof"), f"{cid} carried a profile without profile_asof"

    # a collection that never had a profile must not acquire one
    never = [c for c in out if not c["has_profile"]]
    for c in never:
        assert not by_id[c["id"]]["has_profile"], f"{c['id']} lost a profile"

    # no previous file at all: nothing carried, nothing raised
    assert carry_forward(copy.deepcopy(out), os.path.join(HERE, "nope.json")) == 0

    print(f"ok — {kept} profiles carried over, {len(never)} legitimately without one")


if __name__ == "__main__":
    main()
