"""
Backfill Year column into all existing CSV files.
Extracts year from the Link field (e.g., .../2004-nissan-... → 2004).
Usage: python backfill_year.py
"""
import pandas as pd
import re
import os
import glob
from pathlib import Path

DATA_RAW_DIR = Path("data/raw")


def extract_year_from_link(link):
    match = re.search(r'/(\d{4})-', str(link))
    return match.group(1) if match else None


def main():
    csv_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))
    total = len(csv_files)

    for idx, filepath in enumerate(csv_files, 1):
        filename = os.path.basename(filepath)
        df = pd.read_csv(filepath)

        if 'Year' in df.columns and df['Year'].notna().all():
            continue

        df['Year'] = df['Link'].apply(extract_year_from_link)
        df['Year'] = df['Year'].fillna('N/A')

        cols = list(df.columns)
        if 'Year' in cols:
            cols.remove('Year')
            model_idx = cols.index('Model')
            cols.insert(model_idx + 1, 'Year')

        df = df[cols]
        df.to_csv(filepath, index=False)

        if idx % 100 == 0:
            print(f"  Processed {idx}/{total} files...")

    print(f"Done. {total} files processed.")


if __name__ == '__main__':
    main()
