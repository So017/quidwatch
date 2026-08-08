# Quidwatch data pipeline (v1)

Pulls Bank of England and ONS data, computes the "real savings rate"
metric, and outputs a monthly dataset the frontend can read.

## What's in here

```
src/
  fetch_boe.py       fetch + parse Bank Rate & effective deposit rates
  fetch_ons.py        fetch + parse CPI annual inflation rate
  build_dataset.py   merge BoE + ONS, compute derived metrics
  run_pipeline.py    single entrypoint that runs the whole thing
tests/
  test_parsing.py    unit tests using fixture data (no network needed)
.github/workflows/
  update_data.yml    runs the pipeline weekly, commits new data
data/
  raw/               raw pulls, one CSV per source
  processed/         quidwatch_monthly.csv/json + latest.json
```

## Data sources (both free, no API key)

| Series | Source | Code | What it is |
|---|---|---|---|
| Bank Rate | BoE IADB | `IUDBEDR` | The MPC's official interest rate |
| Sight deposit effective rate | BoE IADB | `Z6IQ` | Avg rate on household current-account-style deposits |
| Time deposit effective rate | BoE IADB | `Z6IW` | Avg rate on household notice/fixed-term savings |
| CPI annual rate | ONS (MM23 dataset) | `D7G7` | Headline 12-month inflation rate |

Both are official free public endpoints, licensed under the Open
Government Licence v3.0. No scraping of a commercial site, no ToS risk.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

## Run the tests first

This checks the parsing logic against fixture data - no network call, so
it should just work:

```bash
pytest tests/ -v
```

## Run the real pipeline

This hits the live BoE and ONS endpoints:

```bash
python src/run_pipeline.py
```

Check `data/processed/quidwatch_monthly.csv` and `latest.json` afterwards
- open them and sanity-check the numbers against the BoE/ONS websites
directly before trusting them in anything published.

## Decision you need to make before publishing anything

`build_dataset.py` computes the real savings rate against **both** the
sight-deposit rate and the time-deposit rate. You need to pick one as
"the" headline figure (or present both) - read BoE's own definitions of
sight vs. time deposits first:
https://www.bankofengland.co.uk/statistics/details/further-details-about-effective-interest-rates-data

Whichever you pick, say why in the site's footer/about text. That
reasoning is the actual data-analysis judgement call - worth being able
to explain in an interview.

## Automation

`.github/workflows/update_data.yml` runs `run_pipeline.py` every Monday
and commits the refreshed data straight to the repo. No secrets or API
keys needed - just push this repo to GitHub and enable Actions.
