"""
Fetch time series from the Bank of England's Interactive Statistical
Database (IADB). No API key needed - it's a public CSV endpoint.

Verified endpoint pattern (checked directly against bankofengland.co.uk):
https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp
    ?csv.x=yes
    &Datefrom=01/Jan/2000
    &Dateto=01/Oct/2024
    &SeriesCodes=IUDBEDR,CFMZ6IQ,CFMZ6IW
    &CSVF=TN
    &UsingCodes=Y
    &VPD=Y
    &VFD=N

Series codes used by Quidwatch v1 (all confirmed against the live
database, 2026-08 - two earlier guesses were wrong, see SERIES_LABELS
comment below):
    IUDBEDR  - Bank Rate (the MPC's official rate)
    CFMZ6IQ  - Effective rate, household sight/instant-access deposits (Table G1.4)
    CFMZ6IW  - Effective rate, household time deposits (Table G1.4)
"""

from io import StringIO

import pandas as pd
import requests

BOE_BASE_URL = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"

# Some government sites reject requests that don't look like they're
# coming from a real browser (no User-Agent = obvious script). This is
# a plain, honest header set - not trying to impersonate anything, just
# not leaving the default "python-requests/x.x" identifier that some
# servers block outright.
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.bankofengland.co.uk/boeapps/iadb/",
}

# Human-readable names for the series we track. Extend this as the site grows.
# Confirmed live and actively publishing (2026-08) - earlier attempts
# (Z6IQ/Z6IW, then IUMWTTA) either didn't exist or had gone stale.
SERIES_LABELS = {
    "IUDBEDR": "bank_rate",
    "CFMZ6IQ": "instant_access_deposit_rate",  # Table G1.4, effective/blended rate
    "CFMZ6IW": "time_deposit_rate",            # Table G1.4, effective rate
    "IUMB6VK": "instant_access_quoted_rate",   # Table G1.3, quoted rate excl. bonus -
                                                 # the "loyalty penalty" gap vs the
                                                 # blended CFMZ6IQ rate above
}


def _parse_boe_csv(csv_text: str) -> pd.DataFrame:
    """
    Pure parsing logic, no network call - this is what tests/test_parsing.py
    exercises directly with fixture text, so we can verify the parsing is
    correct without hitting the live BoE endpoint every time.
    """
    raw = pd.read_csv(StringIO(csv_text))

    # First column is the date, named something like "DATE" or blank -
    # normalise it regardless of what the export calls it.
    raw = raw.rename(columns={raw.columns[0]: "date"})
    raw["date"] = pd.to_datetime(raw["date"], format="%d %b %Y", errors="coerce")
    raw = raw.dropna(subset=["date"])

    # Wide -> long, so every row is one (date, series, value) observation.
    long_df = raw.melt(id_vars="date", var_name="series_code", value_name="value")
    long_df["value"] = pd.to_numeric(long_df["value"], errors="coerce")
    long_df = long_df.dropna(subset=["value"])
    long_df["series_name"] = long_df["series_code"].map(SERIES_LABELS).fillna(long_df["series_code"])

    return long_df.sort_values(["series_code", "date"]).reset_index(drop=True)


def fetch_boe_series(series_codes: list[str], date_from: str, date_to: str) -> pd.DataFrame:
    """
    Fetch one or more BoE series and return a tidy long-format DataFrame:
    columns = [date, series_code, value, series_name]

    date_from / date_to must be in the BoE format, e.g. "01/Jan/2000"
    """
    params = {
        "csv.x": "yes",
        "Datefrom": date_from,
        "Dateto": date_to,
        "SeriesCodes": ",".join(series_codes),
        "CSVF": "TN",
        "UsingCodes": "Y",
        "VPD": "Y",
        "VFD": "N",
    }

    resp = requests.get(BOE_BASE_URL, params=params, headers=REQUEST_HEADERS, timeout=30)

    if resp.status_code != 200:
        # Print the first part of what the server actually sent back -
        # a 403 page's text often explains why (e.g. rate limiting,
        # maintenance, blocked headers) more usefully than the status
        # code alone.
        print(f"BoE request failed: HTTP {resp.status_code}")
        print("Response body preview:")
        print(resp.text[:500])

    resp.raise_for_status()

    return _parse_boe_csv(resp.text)


if __name__ == "__main__":
    # Quick manual check - run `python src/fetch_boe.py` to see it working.
    df = fetch_boe_series(
        list(SERIES_LABELS.keys()),
        date_from="01/Jan/2020",
        date_to="01/Jan/2026",
    )
    print(df.tail(10))
    df.to_csv("data/raw/boe_raw.csv", index=False)
    print(f"\nSaved {len(df)} rows to data/raw/boe_raw.csv")
