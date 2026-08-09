# Quidwatch data pipeline

Pulls Bank of England and ONS data, computes the real savings rate and
the "loyalty gap" between new-customer and existing-customer savings
rates, and outputs a monthly dataset the frontend reads directly.

## What's in here

```
index.html                homepage (reads data/processed/ at runtime)
articles/                 standalone analysis pieces
assets/style.css          shared design system for all pages
src/
  fetch_boe.py             fetch + parse Bank Rate & deposit rate series
  fetch_ons.py             fetch + parse CPI annual inflation rate
  build_dataset.py         merge BoE + ONS, compute derived metrics
  run_pipeline.py          single entrypoint that runs the whole thing
tests/
  test_parsing.py          unit tests using fixture data (no network needed)
.github/workflows/
  update_data.yml          runs the pipeline weekly, commits new data
data/
  raw/                     raw pulls, one CSV per source
  processed/               quidwatch_monthly.csv/json + latest.json
```

## Data sources (all free, no API key)

| Series | Source | Code | What it is |
|---|---|---|---|
| Bank Rate | BoE IADB | `IUDBEDR` | The MPC's official interest rate |
| Instant-access deposit rate | BoE IADB (Table G1.4) | `CFMZ6IQ` | Effective/blended rate across existing instant-access accounts |
| Time deposit rate | BoE IADB (Table G1.4) | `CFMZ6IW` | Effective/blended rate across existing time deposits |
| Quoted instant-access rate | BoE IADB (Table G1.3) | `IUMB6VK` | Rate quoted to new customers, excl. bonus |
| CPI annual rate | ONS (MM23 dataset) | `D7G7` | Headline 12-month inflation rate |

All are official free public endpoints, licensed under the Open
Government Licence v3.0. No scraping of a commercial site, no ToS risk.
The BoE endpoint requires browser-like request headers (User-Agent,
Accept, Referer) or it returns a 403 - see `fetch_boe.py`.

## Derived metrics

- **Real savings rate** = time deposit rate minus CPI (the site's headline figure)
- **Loyalty gap** = quoted rate minus the existing-customer instant-access rate - how much more a new customer is offered than an existing saver actually receives

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run the tests first

Checks the parsing logic against fixture data - no network call needed:

```bash
pytest tests/ -v
```

## Run the real pipeline

Hits the live BoE and ONS endpoints:

```bash
python src/run_pipeline.py
```

Check `data/processed/quidwatch_monthly.csv` and `latest.json` afterwards -
open them and sanity-check the numbers against the BoE/ONS websites
directly before trusting them in anything published.

## Methodology decisions already made (documented for anyone reading this)

- **Headline real rate uses time deposits, not instant-access.** Instant-access
  accounts behave more like current accounts; time deposits are the closer
  match to "a savings account" in common usage.
- **Effective rates (Table G1.4), not quoted rates (Table G1.3), are used
  for the main comparison.** Effective rates reflect what savers are
  actually earning on average, including people who never switch - the
  quoted rate only appears as the second half of the loyalty-gap
  comparison, not as the headline figure.

## Automation

`.github/workflows/update_data.yml` runs `run_pipeline.py` every Monday
and commits the refreshed data straight to the repo. No secrets or API
keys needed - just push this repo to GitHub and enable Actions. Note
that the underlying BoE/ONS data itself only updates monthly - the
weekly schedule just means the site checks for new data promptly once
it's published, not that new figures appear every week.

## Local preview

Browsers block a webpage from reading a local file directly, so
`index.html` needs to be served, not opened by double-clicking:

```bash
python -m http.server 8000
```

Then visit `http://localhost:8000`.
