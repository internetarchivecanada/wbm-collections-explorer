# The serverless edition

`build.py` bakes the whole explorer into a directory of plain files. There is no
runtime, no database and no process to keep alive — every page is rendered at
build time from `app/data/collections.json`, and all the interactivity (filter,
sort, tiles/table, theme, per-collection search) was already client-side, so
nothing is lost by removing the server.

```sh
pip install -r requirements-build.txt
python3 app/refresh.py          # optional: re-harvest from the Wayback Machine
python3 build.py                # -> ./dist
python3 check_build.py dist     # every page present, every local link resolves
```

Open `dist/index.html` directly, or `python3 -m http.server --directory dist`.

## What comes out

```
dist/
  index.html               tile + table view of all 49 collections
  c/<id>/index.html        one detail page per collection
  404.html                 custom not-found page
  api/collections.json     the JSON API, as a static file
  healthz.json             the /healthz payload, as a static file
  sitemap.xml, robots.txt  only with --site-url
  static/app.css, app.js
  .nojekyll                stops GitHub Pages from running Jekyll over it
```

The routes are identical to the server edition's, so a URL that worked against
Flask works against the static build. About 0.9 MB in total.

## Link style — the one thing to get right

| | |
|---|---|
| `python3 build.py` | **relative** links. Works at any path prefix, and straight off the filesystem over `file://`. |
| `python3 build.py --base /wbm-collections-explorer/` | **root-absolute** links, for a GitHub Pages *project* site. |

Relative is the more portable default, with one limitation: a static host serves
`404.html` for *any* missing path, so its relative links only resolve when the
missing path was at the root. `--base` fixes that, which is why CI always passes
it. `check_build.py` verifies whichever mode you built.

## How it shares code with the server

`app/core.py` holds everything that is neither Flask nor Jinja: the data load,
the `commas` / `compact` / `lang` / `api_html` filters, `age_phrase` and
`enrich`. `app/app.py` and `build.py` both import it and both render the *same*
templates in `app/templates/`, so the two editions cannot drift.

`build.py` supplies its own four-endpoint `url_for` in place of Flask's — that
is the entire difference between the two.

## Deployment

`.github/workflows/deploy.yml` builds and publishes to GitHub Pages on every
push to `main`, nightly at 16:30 UTC, and on demand via *Run workflow*.

Every run starts by fetching the dataset the studio deployment publishes,
`https://wayback-labs.sf.archive.org/collections/api/collections.json`, with
`fetch_snapshot.py`. The studio re-harvests web.archive.org every morning at
06:45 Pacific from inside the Internet Archive network and is done in about ten
minutes; the cron runs at least an hour after that, all year.

CI used to run `app/refresh.py` itself. That stopped working: web.archive.org
refuses or throttles a share of requests from GitHub runner IPs, and from
2026-10-01 those requests failed slowly enough that the harvest overran the
45-minute job limit every night and nothing deployed. The studio already has
the data, so there is no reason to fetch it twice from a worse vantage point.

`fetch_snapshot.py` fails closed. It retries three times, then checks the
snapshot: every collection record complete and well-typed, at least 45
collections and 40 profiles, generated within the last 48 hours. If any of that
fails, it writes nothing and exits 1, the job stops before deploying, and Pages
keeps serving the last good site. It deliberately does **not** fall back to the
committed `app/data/collections.json`: that file is older than whatever Pages is
already serving, so building from it would roll the site back. The same applies
to pushes, so a template change cannot deploy while the studio is unreachable;
re-run the workflow once it is back. `test_fetch_snapshot.py` pins all of this
down.

The committed dataset is still what a local `python3 build.py` uses, and the
fixture for both test files. Refresh it from the studio with
`python3 fetch_snapshot.py` and commit the result when it gets stale.

Nothing here is GitHub-specific, though. `dist/` is ordinary static files:
`aws s3 sync dist/ s3://…`, a Caddy `file_server`, Netlify, or an
`archive.org` item all work, and `--base` / `--site-url` are the only knobs.
