# Wayback Collection Search Explorer

A tile-based explorer for every collection in the Wayback Machine's **Collection Search**
drop-down — the 49 separately-built full-text indexes reachable from
<https://web.archive.org/collection-search/>.

Live at `https://wayback-labs.sf.archive.org/collections/` (also `https://208.70.27.170/collections/`).

## Two editions, one set of templates

| | |
|---|---|
| **Server** — `app/app.py` | Flask behind Caddy on the Internet Archive studio host. Deploy notes in [DEPLOY.md](DEPLOY.md). |
| **Serverless** — `build.py` | Renders the same templates to a directory of plain files. No runtime at all. See [SERVERLESS.md](SERVERLESS.md). |

Both import `app/core.py` and render `app/templates/`, so the two cannot drift.
The serverless build exists because nothing here actually needs a server: the
data is a nightly snapshot and every interaction is already client-side.

```sh
pip install -r requirements-build.txt
python3 build.py && python3 check_build.py dist   # -> ./dist, 0.9 MB
```

## What it shows

Each tile carries a consistent, hand-written title and one-line blurb (the API's own titles
are inconsistent — `geocities`, `.gov web pages`, `hk.appledaily.com`, `Local Partisan News,
AKA "Pink Slime"`), plus:

| Field | Where it comes from |
|---|---|
| Document count + unit | `collectioninfo` `count`; the unit ("web pages", "PDF files", "posts") is curated |
| Share of all Collection Search content | derived; drawn as the thin bar under the figure |
| Index freshness (Live / Aging / Frozen) | `collectioninfo` `last_updated` vs today |
| Capture-year span + sparkline | `waybacksearch` `first_captured_year` aggregation |
| Share of URLs now dead on the live web | `waybacksearch` `is_dead` aggregation |
| Top hosts, languages, TLDs | `waybacksearch` `domains` / `languages` / `tlds` aggregations |
| Curator, item date, subjects | `archive.org/metadata/<item>` for the 13 collections that name one |

Views: tile grid or table; filter by one of six curated subject areas; free-text filter;
sort by size, index recency, staleness, title, time span, or dead-link share. Filter state is
in the query string, so a view is shareable (`?cat=press&sort=stale`).

Each tile has its own search box that goes straight to
`web.archive.org/collection-search/<id>/<query>`. `/c/<id>` is a per-collection detail page.

## Data

`app/data/collections.json` is baked by `app/refresh.py` from three public sources:

* `web.archive.org/__wb/search/collectioninfo?collection=all` — the authoritative roster.
  This is what populates the drop-down. It also exposes two collections that are **not** in
  the public menu: `nrc.gov` and `january6th.house.gov`.
* `web.archive.org/__wb/search/waybacksearch?q=*:*&size=0&collection=<id>` — a
  whole-collection profile via the search aggregations. `q=*:*` matches everything, and
  `size=0` asks for aggregations without hits.
* `archive.org/metadata/<item>/metadata`.

**Known limits, surfaced in the UI rather than hidden:**

* The two largest indexes — `pdf` (1.73bn) and `telegram` (3.79bn) — 504 on the aggregation
  call. Those tiles show counts only. `refresh.py` keeps the last good profile on failure.
* Aggregation buckets are capped at the top 17 values, so year/host/language lists are
  "17 busiest", not exhaustive. The UI says so wherever the cap is hit.
* `is_dead` is only populated for some collections; the rest read "not measured".
* Counts are index sizes reported by the Wayback Machine, not counts of distinct URLs.

`refresh.py --cached` rebuilds from `app/cache/` without touching the network.

## Layout

```
build.py               serverless build: templates + data -> dist/ (Jinja2 only, no Flask)
check_build.py         post-build check: every page present, every local link resolves
.github/workflows/     nightly refresh + build + deploy to GitHub Pages
run.sh                 launchd entry point → app/venv/bin/python app.py on $PORT (8331)
refresh.sh             nightly data rebuild (06:45), launchd com.wbmstudio.collections-refresh
caddy                  Caddy snippet: /collections/* → 127.0.0.1:8331
launchd.plist          com.wbmstudio.collections
launchd-refresh.plist  com.wbmstudio.collections-refresh
.menu                  landing-page tile (emoji ⇥ title ⇥ description)
app/app.py             Flask; honours X-Forwarded-Prefix so it works under /collections/
app/core.py            data load, template filters and derived fields — shared by both editions
app/curation.py        the 49 curated titles, blurbs, units and subject areas
app/refresh.py         harvester → app/data/collections.json
app/templates/         base / index / detail / 404
app/static/            app.css, app.js
```

## Operating it

```sh
service status collections
service logs collections
sudo launchctl kickstart -k system/com.wbmstudio.collections     # restart
cd /opt/services/collections/app && ./venv/bin/python refresh.py # rebuild data now
curl -s localhost:8331/healthz
```

Adding a collection: the roster is discovered automatically, but a new id will fall back to
the Wayback API's own title and land in "Topics & Events" until it gets an entry in
`app/curation.py`. `refresh.py` prints nothing special for uncurated ids — check
`/healthz` count against the drop-down after a Wayback release.
