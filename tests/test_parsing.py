"""
Tests for the parsing logic in fetch_boe.py and fetch_ons.py.

Important: the CSV text below is a SAMPLE FIXTURE for testing the parser's
shape-handling, not real published BoE/ONS data. Never treat fixture
values as real figures anywhere outside this test file.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fetch_boe import _parse_boe_csv
from fetch_ons import _parse_ons_csv

# --- SAMPLE FIXTURE (fake values, structure only) ---
FAKE_BOE_CSV = """DATE,IUDBEDR,Z6IQ,Z6IW
31 Jan 2024,5.25,1.20,3.10
29 Feb 2024,5.25,1.22,3.15
31 Mar 2024,5.00,1.18,3.05
"""

# --- SAMPLE FIXTURE (fake values, structure only) ---
# Mirrors the real ONS export shape: a metadata block, then rows mixing
# annual / quarterly / monthly periods in one column.
FAKE_ONS_CSV = """"Title","CPI ANNUAL RATE 00: ALL ITEMS (SAMPLE)"
"CDID","D7G7"
"PreUnit",""
"Unit","%"
"Release Date","01-01-2024"
""
"2023","4.0"
"2023 Q4","3.9"
"2023 OCT","4.6"
"2023 NOV","3.9"
"2023 DEC","4.0"
"2024","3.2"
"2024 Q1","3.4"
"2024 JAN","4.0"
"2024 FEB","3.4"
"2024 MAR","3.2"
"""


def test_parse_boe_csv_shapes_wide_to_long():
    df = _parse_boe_csv(FAKE_BOE_CSV)

    # 3 dates x 3 series = 9 rows in long format
    assert len(df) == 9
    assert set(df["series_code"]) == {"IUDBEDR", "Z6IQ", "Z6IW"}
    assert set(df.columns) == {"date", "series_code", "value", "series_name"}

    bank_rate_rows = df[df["series_code"] == "IUDBEDR"].sort_values("date")
    assert list(bank_rate_rows["value"]) == [5.25, 5.25, 5.00]
    assert bank_rate_rows["series_name"].iloc[0] == "bank_rate"


def test_parse_ons_csv_keeps_only_monthly_rows():
    df = _parse_ons_csv(FAKE_ONS_CSV, cdid="D7G7")

    # Should drop the "2023", "2023 Q4", "2024", "2024 Q1" rows and keep
    # only the 6 genuine monthly rows (Oct/Nov/Dec 2023, Jan/Feb/Mar 2024).
    assert len(df) == 6
    assert df["series_code"].unique().tolist() == ["D7G7"]
    assert df["series_name"].unique().tolist() == ["cpi_annual_rate"]

    values = df.sort_values("date")["value"].tolist()
    assert values == [4.6, 3.9, 4.0, 4.0, 3.4, 3.2]


def test_parse_ons_csv_handles_missing_or_malformed_rows_gracefully():
    messy = FAKE_ONS_CSV + '"2024 XYZ","not-a-number"\n'  # bad month code + bad value
    df = _parse_ons_csv(messy, cdid="D7G7")
    # The malformed row should simply be dropped, not raise an exception.
    assert len(df) == 6


if __name__ == "__main__":
    test_parse_boe_csv_shapes_wide_to_long()
    test_parse_ons_csv_keeps_only_monthly_rows()
    test_parse_ons_csv_handles_missing_or_malformed_rows_gracefully()
    print("All parsing tests passed.")
