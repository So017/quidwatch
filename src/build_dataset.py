"""
Merge the BoE and ONS raw pulls into a single monthly dataset and compute
the derived metrics Quidwatch actually publishes.

This script does NOT make your methodology decisions for you - see the
DECISION comment below. That choice (and being able to explain it) is
the part that's genuinely yours.
"""

import json
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def _to_monthly(df: pd.DataFrame, series_code: str) -> pd.Series:
    """Collapse a (possibly daily/irregular) BoE series to one value per calendar month."""
    s = df[df["series_code"] == series_code].set_index("date")["value"]
    s.index = pd.to_datetime(s.index)
    return s.resample("MS").last()  # last observed value in the month


def build_dataset(
    boe_raw_path: Path = RAW_DIR / "boe_raw.csv",
    ons_raw_path: Path = RAW_DIR / "ons_raw.csv",
) -> pd.DataFrame:
    boe = pd.read_csv(boe_raw_path, parse_dates=["date"])
    ons = pd.read_csv(ons_raw_path, parse_dates=["date"])

    bank_rate = _to_monthly(boe, "IUDBEDR")
    instant_access_rate = _to_monthly(boe, "CFMZ6IQ")
    time_rate = _to_monthly(boe, "CFMZ6IW")
    instant_access_quoted = _to_monthly(boe, "IUMB6VK")

    cpi_series = ons.set_index("date")["value"]
    cpi_series.index = pd.to_datetime(cpi_series.index).to_period("M").to_timestamp()
    cpi = cpi_series.resample("MS").last()

    merged = pd.DataFrame(
        {
            "bank_rate": bank_rate,
            "instant_access_deposit_rate": instant_access_rate,
            "time_deposit_rate": time_rate,
            "instant_access_quoted_rate": instant_access_quoted,
            "cpi_annual_rate": cpi,
        }
    ).dropna(how="all")

    # DECISION (yours to make, not mine): which deposit series represents
    # "the average saver" for the headline real-rate figure on the homepage?
    # v1 computes both so you can compare them before deciding. My working
    # assumption below is that time deposits (notice/fixed-term) are the
    # closer match to what people mean by "a savings account", since
    # instant-access accounts behave more like current accounts - but
    # confirm this against BoE's own product definitions before you
    # publish it, and note your reasoning in the site's footer/about text.
    merged["real_rate_time_deposits"] = merged["time_deposit_rate"] - merged["cpi_annual_rate"]
    merged["real_rate_instant_access"] = merged["instant_access_deposit_rate"] - merged["cpi_annual_rate"]

    # The "loyalty penalty" gap: how much more a new customer is quoted
    # vs. what the average existing saver is actually receiving. This is
    # a genuine, sourced phenomenon (FCA has investigated it directly) -
    # not an editorial judgement call like the DECISION above.
    merged["loyalty_gap"] = merged["instant_access_quoted_rate"] - merged["instant_access_deposit_rate"]

    merged = merged.reset_index().rename(columns={"index": "date"})
    return merged.sort_values("date").reset_index(drop=True)


def save_outputs(df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(PROCESSED_DIR / "quidwatch_monthly.csv", index=False)
    df.to_json(PROCESSED_DIR / "quidwatch_monthly.json", orient="records", date_format="iso", indent=2)

    complete = df.dropna(subset=["cpi_annual_rate", "time_deposit_rate", "instant_access_quoted_rate"])
    if complete.empty:
        print("Warning: no complete rows yet to build latest.json")
        return

    latest = complete.iloc[-1]
    summary = {
        "as_of": latest["date"].strftime("%Y-%m-%d"),
        "bank_rate": latest["bank_rate"],
        "cpi_annual_rate": latest["cpi_annual_rate"],
        "time_deposit_rate": latest["time_deposit_rate"],
        "instant_access_deposit_rate": latest["instant_access_deposit_rate"],
        "instant_access_quoted_rate": latest["instant_access_quoted_rate"],
        "real_rate_time_deposits": latest["real_rate_time_deposits"],
        "real_rate_instant_access": latest["real_rate_instant_access"],
        "loyalty_gap": latest["loyalty_gap"],
    }
    with open(PROCESSED_DIR / "latest.json", "w") as f:
        json.dump(summary, f, indent=2, default=str)


if __name__ == "__main__":
    dataset = build_dataset()
    save_outputs(dataset)
    print(dataset.tail(6).to_string(index=False))
    print("\nSaved quidwatch_monthly.csv / .json / latest.json to data/processed/")
