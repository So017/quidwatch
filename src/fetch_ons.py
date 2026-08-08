"""
Fetch a time series from the ONS website's CSV generator.

Verified endpoint pattern (checked directly against ons.gov.uk):
https://www.ons.gov.uk/generator?format=csv&uri=/economy/inflationandpriceindices/timeseries/{cdid}/mm23

This is NOT the ONS Beta API (api.beta.ons.gov.uk) - that API does not
carry headline series like CPI. This is the classic per-series CSV export,
free, no key required, licensed under the Open Government Licence v3.0.

CDID codes used by Quidwatch v1:
    D7G7 - CPI, 12-month (annual) inflation rate, all items
"""

import re
from io import StringIO

import pandas as pd
import requests

ONS_GENERATOR_URL = "https://www.ons.gov.uk/generator"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/csv,text/plain,*/*",
}

SERIES_LABELS = {
    "D7G7": "cpi_annual_rate",
}

# Matches rows like "2026 JUN" - i.e. genuine monthly observations.
# ONS export files mix annual ("2026"), quarterly ("2026 Q2") and monthly
# ("2026 JUN") rows in the same file, so we filter down to monthly only.
_MONTHLY_PATTERN = re.compile(r"^\d{4} [A-Z]{3}$")


def _parse_ons_csv(csv_text: str, cdid: str) -> pd.DataFrame:
    """
    Pure parsing logic, no network call - exercised directly by
    tests/test_parsing.py with fixture text.

    ONS CSV exports carry a metadata header block before the data rows.
    Rather than assume a fixed number of header lines (fragile - it has
    changed before), we parse everything and keep only rows whose first
    column matches the monthly period pattern, e.g. "2026 JUN".
    """
    raw = pd.read_csv(StringIO(csv_text), header=None, names=["period", "value"], dtype=str, on_bad_lines="skip")

    monthly = raw[raw["period"].str.match(_MONTHLY_PATTERN, na=False)].copy()
    monthly["date"] = pd.to_datetime(monthly["period"], format="%Y %b", errors="coerce")
    monthly["value"] = pd.to_numeric(monthly["value"], errors="coerce")
    monthly = monthly.dropna(subset=["date", "value"])

    monthly["series_code"] = cdid
    monthly["series_name"] = SERIES_LABELS.get(cdid, cdid)

    return monthly[["date", "series_code", "series_name", "value"]].sort_values("date").reset_index(drop=True)


def fetch_ons_series(cdid: str, dataset: str = "mm23") -> pd.DataFrame:
    """
    Fetch one ONS series by its CDID code and return a tidy DataFrame:
    columns = [date, series_code, series_name, value]
    Only monthly observations are kept.
    """
    params = {
        "format": "csv",
        "uri": f"/economy/inflationandpriceindices/timeseries/{cdid.lower()}/{dataset}",
    }

    resp = requests.get(ONS_GENERATOR_URL, params=params, headers=REQUEST_HEADERS, timeout=30)

    if resp.status_code != 200:
        print(f"ONS request failed: HTTP {resp.status_code}")
        print("Response body preview:")
        print(resp.text[:500])

    resp.raise_for_status()

    return _parse_ons_csv(resp.text, cdid)


if __name__ == "__main__":
    df = fetch_ons_series("D7G7")
    print(df.tail(10))
    df.to_csv("data/raw/ons_raw.csv", index=False)
    print(f"\nSaved {len(df)} rows to data/raw/ons_raw.csv")
