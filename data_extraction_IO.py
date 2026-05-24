#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

@author: Clément HENNET
"""

"""
DB1B Data Downloader
Downloads all quarterly DB1B files (Market, Coupon, Ticket) for a range of years,
then merges each table type into a single DataFrame saved as CSV.

Note: DB1B data is available from 1993 onwards.
"""
##############
## PACKAGES ##
##############

import os
import zipfile
import requests
import pandas as pd
from pathlib import Path

###################
## Configuration ##
###################

OUTPUT_DIR = Path("/Users/.../Project/Datasets")
TEMP_DIR   = OUTPUT_DIR / "raw_downloads"       # zips + extracted CSVs saved here
YEARS      = range(2018, 2020)                  # Run by batch, else you computer will crash ;)
QUARTERS   = range(1, 5)                        # To get Q1, Q2, Q3, Q4 put (1,5)
TABLES     = ["Market"]
# TABLES     = ["Market", "Coupon", "Ticket"]   # To prevent your computer from crashing download only one table at a time
TIMEOUT    = 600                                # seconds (10 min) -> crash guard

###########
## Setup ##
###########

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEMP_DIR.mkdir(parents=True, exist_ok=True)

########################
## Download & extract ##
########################

def download_db1b(year, quarter, table):
    """Download and unzip one DB1B file. Returns path to the extracted CSV."""
    url = (
        f"https://transtats.bts.gov/PREZIP/"
        f"Origin_and_Destination_Survey_DB1B{table}_{year}_{quarter}.zip"
    )
    zip_path = TEMP_DIR / f"db1b_{year}_Q{quarter}_{table}.zip"
    extract_dir = TEMP_DIR / f"db1b_{year}_Q{quarter}_{table}"
    extract_dir.mkdir(exist_ok=True)

    # Skip if already downloaded
    if any(extract_dir.glob("*.csv")):
        print(f"  [skip] {table} {year} Q{quarter} already extracted.")
        return extract_dir

    print(f"  Downloading {table} {year} Q{quarter} ...")
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1 MB chunks
                f.write(chunk)

    print(" Extracting ...")
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(extract_dir)

    zip_path.unlink()  # delete zip to save space
    print(f"  Done -> {extract_dir}")
    return extract_dir

###############
## Main loop ##
###############

# Store per-table list of DataFrames for merging
all_dfs = {table: [] for table in TABLES}

for table in TABLES:
    print(f"\n{'='*50}")
    print(f"  TABLE: {table}")
    print(f"{'='*50}")
    for year in YEARS:
        for quarter in QUARTERS:
            try:
                extract_dir = download_db1b(year, quarter, table)
                csv_files = list(extract_dir.glob("*.csv"))
                if not csv_files:
                    print(f"  [warning] No CSV found for {table} {year} Q{quarter}")
                    continue
                df = pd.read_csv(csv_files[0], low_memory=False)
                df["year"]    = year       # tag with year/quarter for tracking
                df["quarter"] = quarter
                all_dfs[table].append(df)
                print(f"  Loaded {table} {year} Q{quarter}: {df.shape[0]:,} rows")
            except Exception as e:
                print(f"  [error] {table} {year} Q{quarter}: {e}")

########################
## Save independently ##
########################

import shutil
from pathlib import Path

TEMP_DIR   = Path("/Users/clementhennet/Documents/PSE/IO/Project/Datasets/raw_downloads")
MARKET_DIR = Path("/Users/clementhennet/Documents/PSE/IO/Project/Datasets/Market_Data")
TICKET_DIR = Path("/Users/clementhennet/Documents/PSE/IO/Project/Datasets/Ticket_Data")

MARKET_DIR.mkdir(exist_ok=True)

# Find all extracted Market CSVs
csv_files = sorted(TEMP_DIR.glob("db1b_*_Q*_Market/*.csv"))

print(f"Found {len(csv_files)} CSV files")

for f in csv_files:
    parts    = f.parent.name.split("_")   # eg: db1b_1993_Q1_Market
    year     = parts[1]
    quarter  = parts[2]
    new_name = f"DB1B_Market_{year}_{quarter}.csv"
    dest     = MARKET_DIR / new_name
    shutil.copy2(f, dest)
    print(f"  Copied -> {new_name}")

print(f"\nDone. All files in: {MARKET_DIR}")

############################
## OPTION: Merge and save ##
############################

print(f"\n{'='*50}")
print("  Merging and saving ...")
print(f"{'='*50}")

for table, dfs in all_dfs.items():
    if not dfs:
        print(f"  [warning] No data collected for {table}, skipping.")
        continue
    merged = pd.concat(dfs, ignore_index=True)
    out_path = OUTPUT_DIR / f"DB1B_{table}_1993_1996.csv"
    merged.to_csv(out_path, index=False)
    print(f"  Saved {table}: {merged.shape[0]:,} rows -> {out_path}")

print("\nAll done.")