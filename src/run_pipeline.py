"""
Full pipeline entrypoint: fetch BoE + ONS data, merge, compute derived
metrics, save outputs. Run this locally with:

    python src/run_pipeline.py

GitHub Actions calls this same script on a schedule - see
.github/workflows/update_data.yml
"""

from pathlib import Path

from fetch_boe import SERIES_LABELS as BOE_SERIES, fetch_boe_series
from fetch_ons import fetch_ons_series
from build_dataset import build_dataset, save_outputs

RAW_DIR = Path("data/raw")

# Pull a long history - BoE effective rates go back to 1999, CPI further
# still. Adjust the start date once you're happy with performance/size.
DATE_FROM = "01/Jan/1999"
DATE_TO_FORMAT = "%d/%b/%Y"


def main():
    import datetime

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    date_to = datetime.date.today().strftime(DATE_TO_FORMAT)

    print(f"Fetching BoE series {list(BOE_SERIES.keys())} from {DATE_FROM} to {date_to} ...")
    boe_df = fetch_boe_series(list(BOE_SERIES.keys()), date_from=DATE_FROM, date_to=date_to)
    boe_df.to_csv(RAW_DIR / "boe_raw.csv", index=False)
    print(f"  saved {len(boe_df)} rows -> data/raw/boe_raw.csv")

    print("Fetching ONS series D7G7 (CPI annual rate) ...")
    ons_df = fetch_ons_series("D7G7")
    ons_df.to_csv(RAW_DIR / "ons_raw.csv", index=False)
    print(f"  saved {len(ons_df)} rows -> data/raw/ons_raw.csv")

    print("Building merged dataset ...")
    dataset = build_dataset()
    save_outputs(dataset)
    print(f"  saved {len(dataset)} rows -> data/processed/")

    print("\nDone. Latest row:")
    print(dataset.tail(1).to_string(index=False))


if __name__ == "__main__":
    main()
