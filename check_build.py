#!/usr/bin/env python3
"""Post-build sanity check: every page present, every local link resolves.

Run by CI before a deploy, and worth running by hand after editing a template.

    python3 check_build.py dist
"""
import json
import os
import re
import sys
import urllib.parse

LINK = re.compile(r'(?:href|src)="([^"]+)"')


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "dist"
    data = json.load(open(os.path.join(root, "api", "collections.json")))
    problems = []

    expected = ["index.html", "404.html", "healthz.json", ".nojekyll",
                "static/app.css", "static/app.js", "api/collections.json"]
    expected += [os.path.join("c", c["id"], "index.html") for c in data["collections"]]
    for rel in expected:
        if not os.path.exists(os.path.join(root, rel)):
            problems.append(f"missing: {rel}")

    pages = 0
    for dirpath, _, files in os.walk(root):
        for name in files:
            if not name.endswith(".html"):
                continue
            pages += 1
            path = os.path.join(dirpath, name)
            html = open(path, encoding="utf-8").read()
            if "{{" in html or "{%" in html:
                problems.append(f"unrendered template syntax: {path}")
            for href in LINK.findall(html):
                if href.startswith(("http://", "https://", "#", "mailto:", "data:")):
                    continue
                target = urllib.parse.unquote(href.split("?")[0].split("#")[0])
                if target.startswith("/"):
                    # root-absolute: resolve against the site root, dropping the
                    # --base prefix the build put on it
                    resolved = os.path.join(root, target.lstrip("/"))
                    if not os.path.exists(resolved) and not os.path.isdir(resolved):
                        parts = target.lstrip("/").split("/", 1)
                        resolved = os.path.join(root, parts[1] if len(parts) > 1 else "")
                else:
                    resolved = os.path.normpath(os.path.join(dirpath, target))
                if os.path.isdir(resolved) or target.endswith("/"):
                    resolved = os.path.join(resolved, "index.html")
                if not os.path.exists(resolved):
                    problems.append(f"dead link: {path} -> {href}")

    for p in problems:
        print("FAIL", p, file=sys.stderr)
    print(f"checked {pages} pages, {len(data['collections'])} collections, "
          f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
