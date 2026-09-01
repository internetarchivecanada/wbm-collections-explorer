#!/usr/bin/env python3
"""Build the serverless (fully static) edition of the Collection Search Explorer.

Renders the same Jinja templates the Flask app serves into a directory of plain
files that any static host will serve — GitHub Pages, S3, a Caddy file_server,
or a local `file://` open. There is no runtime: every page is baked from
app/data/collections.json at build time, and all the interactivity (filter,
sort, tile/table toggle, theme, per-collection search) was already client-side.

    dist/
      index.html                 the tile + table view
      c/<id>/index.html          one detail page per collection
      404.html                   custom not-found page
      api/collections.json       the JSON API, as a static file
      healthz.json               the /healthz payload, as a static file
      sitemap.xml                only with --site-url
      static/app.css, app.js
      .nojekyll                  keep GitHub Pages from running Jekyll

Link style:
  * default          — relative links, so the build works at any path prefix
                       and straight off the filesystem.
  * --base /path/    — root-absolute links. Needed for a GitHub Pages *project*
                       site, and the only way 404.html can link correctly from
                       an arbitrary depth.

    python3 build.py                                 # relative, ./dist
    python3 build.py --base /wbm-collections-explorer/
    python3 build.py --out /tmp/site --site-url https://example.org/x/
"""
import argparse
import json
import os
import shutil
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(HERE, "app")
sys.path.insert(0, APP)

import core  # noqa: E402  (app/core.py — shared with the Flask app)

from jinja2 import Environment, FileSystemLoader, select_autoescape  # noqa: E402


def make_url_for(depth, base):
    """A drop-in for Flask's url_for covering the four endpoints the templates use.

    depth is how many directories deep the page being rendered sits, and is
    ignored when `base` is given (links are then root-absolute).
    """
    up = base if base else ("../" * depth)

    def url_for(endpoint, **kw):
        if endpoint == "static":
            return f"{up}static/{kw['filename']}"
        if endpoint == "index":
            return up or "./"
        if endpoint == "detail":
            return f"{up}c/{urllib.parse.quote(kw['cid'], safe='')}/"
        if endpoint == "api":
            return f"{up}api/collections.json"
        raise ValueError(f"static build has no route for url_for({endpoint!r})")

    return url_for


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=os.path.join(HERE, "dist"),
                    help="output directory (default: ./dist); cleared first")
    ap.add_argument("--base", default="",
                    help="root-absolute path prefix the site is served at, "
                         "e.g. /wbm-collections-explorer/ (default: relative links)")
    ap.add_argument("--site-url", default="",
                    help="absolute site URL; also writes sitemap.xml and robots.txt")
    ap.add_argument("--data", default=core.DATA_PATH, help="path to collections.json")
    args = ap.parse_args()

    base = args.base
    if base and not base.endswith("/"):
        base += "/"
    if base and not base.startswith("/"):
        base = "/" + base

    if not os.path.exists(args.data):
        sys.exit(f"no dataset at {args.data} — run: python3 app/refresh.py")
    data = core.enrich(core.read_data(args.data))

    env = Environment(
        loader=FileSystemLoader(os.path.join(APP, "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters.update(core.FILTERS)

    out = args.out
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)

    def render(template, depth, **ctx):
        env.globals["url_for"] = make_url_for(depth, base)
        return env.get_template(template).render(d=data, version=core.VERSION, **ctx)

    write(os.path.join(out, "index.html"), render("index.html", 0))

    # 404.html is served for any missing path, so relative links from it are only
    # right at the root. With --base they are correct everywhere.
    write(os.path.join(out, "404.html"), render("404.html", 0))
    if not base:
        print("note: no --base, so 404.html links only resolve at the site root")

    for c in data["collections"]:
        write(os.path.join(out, "c", c["id"], "index.html"), render("detail.html", 2, c=c))

    write(os.path.join(out, "api", "collections.json"),
          json.dumps(core.read_data(args.data), indent=1))
    write(os.path.join(out, "healthz.json"), json.dumps({
        "ok": True, "version": core.VERSION, "generated": data["generated"],
        "collections": len(data["collections"]), "serverless": True,
    }, indent=1))

    shutil.copytree(os.path.join(APP, "static"), os.path.join(out, "static"))
    write(os.path.join(out, ".nojekyll"), "")

    if args.site_url:
        site = args.site_url if args.site_url.endswith("/") else args.site_url + "/"
        urls = [site] + [site + "c/" + urllib.parse.quote(c["id"], safe="") + "/"
                         for c in data["collections"]]
        lastmod = data["generated"][:10]
        body = "\n".join(f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod></url>" for u in urls)
        write(os.path.join(out, "sitemap.xml"),
              '<?xml version="1.0" encoding="UTF-8"?>\n'
              '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
              f"{body}\n</urlset>\n")
        write(os.path.join(out, "robots.txt"),
              f"User-agent: *\nAllow: /\nSitemap: {site}sitemap.xml\n")

    files = sum(len(f) for _, _, f in os.walk(out))
    size = sum(os.path.getsize(os.path.join(r, f))
               for r, _, fs in os.walk(out) for f in fs)
    print(f"built {out} — {files} files, {size / 1024 / 1024:.1f} MB, "
          f"{len(data['collections'])} collections, links "
          f"{'absolute under ' + base if base else 'relative'}")


if __name__ == "__main__":
    main()
