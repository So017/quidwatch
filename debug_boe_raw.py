"""
Diagnostic only - not part of the pipeline. Prints the first lines of the
raw text the BoE server actually sends back, so we can see its real shape
instead of assuming.

Run with: python debug_boe_raw.py
Then copy me everything it prints.
"""

import requests

BOE_BASE_URL = "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp"

REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.bankofengland.co.uk/boeapps/iadb/",
}

params = {
    "csv.x": "yes",
    "Datefrom": "01/Jan/2024",
    "Dateto": "01/Mar/2024",
    "SeriesCodes": "IUDBEDR,CFMZ6IQ,CFMZ6IW,IUMB6VK",  # all 4 series together, as the real pipeline requests them
    "CSVF": "TN",
    "UsingCodes": "Y",
    "VPD": "Y",
    "VFD": "N",
}

resp = requests.get(BOE_BASE_URL, params=params, headers=REQUEST_HEADERS, timeout=30)

print(f"Status code: {resp.status_code}")
print(f"Content-Type header: {resp.headers.get('Content-Type')}")
print(f"Total length: {len(resp.text)} characters")
print("=" * 60)
print("First 30 lines of raw response, with line numbers:")
print("=" * 60)

lines = resp.text.splitlines()
for i, line in enumerate(lines[:30], start=1):
    print(f"{i:>3}: {repr(line)}")
