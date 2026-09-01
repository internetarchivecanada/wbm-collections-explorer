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
push to `main`, plus nightly at 06:45 UTC (the same hour the studio deployment
refreshes) and on demand via *Run workflow*.

The nightly run re-harvests from `web.archive.org` first. That step is
`continue-on-error` on purpose: the two largest indexes (`pdf`, 1.73bn, and
`telegram`, 3.79bn) reliably 504 on the aggregation call, and a runner can fail
to reach web.archive.org entirely. In both cases `refresh.py` leaves the
committed dataset in place and the build still produces a complete site — a bad
harvest degrades the data's freshness, never the deploy.

**GitHub Pages needs this repository to be public**, because the
`internetarchivecanada` org is on the free plan and Pages from a private repo
requires a paid one. Until then the workflow builds and checks but cannot
deploy. To turn it on:

```sh
gh repo edit internetarchivecanada/wbm-collections-explorer --visibility public
gh api -X POST repos/internetarchivecanada/wbm-collections-explorer/pages \
  -f 'build_type=workflow'
```

Nothing here is GitHub-specific, though. `dist/` is ordinary static files:
`aws s3 sync dist/ s3://…`, a Caddy `file_server`, Netlify, or an
`archive.org` item all work, and `--base` / `--site-url` are the only knobs.
