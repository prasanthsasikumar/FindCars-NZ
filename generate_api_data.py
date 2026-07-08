"""
Generate pre-computed JSON API data files for static Netlify hosting.
Run this locally after scraping to produce the JSON files the static site needs.
Usage: python generate_api_data.py
"""
import pandas as pd
import datetime
import json
import os
import glob
from pathlib import Path

DATA_RAW_DIR = Path("data/raw")
DATA_PROCESSED_DIR = Path("data/processed")
DATA_API_DIR = Path("data/api")


def clean_price(price_str):
    if pd.isna(price_str) or str(price_str) == 'N/A':
        return None
    try:
        return float(str(price_str).replace('$', '').replace(',', '').strip())
    except (ValueError, AttributeError):
        return None


def clean_mileage(mileage_str):
    if pd.isna(mileage_str) or str(mileage_str) == 'N/A':
        return None
    try:
        return float(str(mileage_str).replace(',', '').strip())
    except (ValueError, AttributeError):
        return None


def get_latest_data_file():
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    today_file = DATA_RAW_DIR / f"car_data_{today}.csv"
    yesterday_file = DATA_RAW_DIR / f"car_data_{yesterday}.csv"

    if today_file.exists():
        return today_file
    elif yesterday_file.exists():
        return yesterday_file
    else:
        files = sorted(DATA_RAW_DIR.glob("car_data_*.csv"))
        return files[-1] if files else None


def generate_overview():
    recent_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))[-30:]
    data_frames = [pd.read_csv(f) for f in recent_files if os.path.exists(f)]

    if not data_frames:
        return None

    df = pd.concat(data_frames, ignore_index=True)
    df['Price_Clean'] = df['Price'].apply(clean_price)
    df['Mileage_Clean'] = df['Mileage'].apply(clean_mileage)

    valid_prices = df['Price_Clean'].dropna()
    valid_mileage = df['Mileage_Clean'].dropna()

    overview = {
        'total_listings': int(len(df)),
        'unique_vehicles': int(df['Link'].nunique() if 'Link' in df else 0),
        'manufacturers': int(df['Manufacturer'].nunique()),
        'avg_price': float(round(valid_prices.mean(), 2)) if len(valid_prices) > 0 else 0,
        'median_price': float(round(valid_prices.median(), 2)) if len(valid_prices) > 0 else 0,
        'min_price': float(round(valid_prices.min(), 2)) if len(valid_prices) > 0 else 0,
        'max_price': float(round(valid_prices.max(), 2)) if len(valid_prices) > 0 else 0,
        'avg_mileage': float(round(valid_mileage.mean(), 2)) if len(valid_mileage) > 0 else 0,
        'top_manufacturers': {k: int(v) for k, v in df['Manufacturer'].value_counts().head(10).to_dict().items()},
        'fuel_types': {k: int(v) for k, v in df['Fuel Type'].value_counts().to_dict().items()} if 'Fuel Type' in df else {},
        'registration_status': {k: int(v) for k, v in df['Registration Status'].value_counts().to_dict().items()}
    }
    return overview


def generate_price_trends():
    csv_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))

    trends = []
    for file in csv_files[::7]:
        date_str = Path(file).stem.replace('car_data_', '')
        df = pd.read_csv(file)
        df['Price_Clean'] = df['Price'].apply(clean_price)

        valid_prices = df['Price_Clean'].dropna()

        if len(valid_prices) > 0:
            trends.append({
                'date': date_str,
                'avg_price': float(round(valid_prices.mean(), 2)),
                'median_price': float(round(valid_prices.median(), 2)),
                'count': int(len(df))
            })

    return trends


def generate_manufacturers():
    recent_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))[-30:]
    data_frames = [pd.read_csv(f) for f in recent_files]
    df = pd.concat(data_frames, ignore_index=True)

    df['Price_Clean'] = df['Price'].apply(clean_price)
    df = df[df['Price_Clean'].notna()]

    manufacturer_stats = df.groupby('Manufacturer').agg({
        'Price_Clean': ['mean', 'median', 'count'],
        'Model': 'nunique'
    }).round(2)

    result = []
    for mfg in manufacturer_stats.index:
        result.append({
            'manufacturer': mfg,
            'avg_price': float(manufacturer_stats.loc[mfg, ('Price_Clean', 'mean')]),
            'median_price': float(manufacturer_stats.loc[mfg, ('Price_Clean', 'median')]),
            'count': int(manufacturer_stats.loc[mfg, ('Price_Clean', 'count')]),
            'unique_models': int(manufacturer_stats.loc[mfg, ('Model', 'nunique')])
        })

    result.sort(key=lambda x: x['count'], reverse=True)
    return result[:50]


def generate_damage_analysis():
    recent_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))[-30:]
    data_frames = [pd.read_csv(f) for f in recent_files]
    df = pd.concat(data_frames, ignore_index=True)

    damage_keywords = [
        'Front Damage', 'Rear Damage', 'Left', 'Right',
        'Airbags Deployed', 'Water Damage', 'Fire Damage',
        'Vandalised', 'Stolen', 'Impact Heavy', 'Impact Medium', 'Impact Light'
    ]

    damage_counts = {}
    for keyword in damage_keywords:
        count = df['Damage description'].str.contains(keyword, case=False, na=False).sum()
        if count > 0:
            damage_counts[keyword] = int(count)

    return damage_counts


def generate_price_distribution():
    recent_files = sorted(glob.glob(str(DATA_RAW_DIR / "car_data_*.csv")))[-30:]
    data_frames = [pd.read_csv(f) for f in recent_files]
    df = pd.concat(data_frames, ignore_index=True)

    df['Price_Clean'] = df['Price'].apply(clean_price)
    valid_prices = df['Price_Clean'].dropna()

    distribution = {
        '$0-$500': int(((valid_prices >= 0) & (valid_prices < 500)).sum()),
        '$500-$1k': int(((valid_prices >= 500) & (valid_prices < 1000)).sum()),
        '$1k-$2k': int(((valid_prices >= 1000) & (valid_prices < 2000)).sum()),
        '$2k-$5k': int(((valid_prices >= 2000) & (valid_prices < 5000)).sum()),
        '$5k-$10k': int(((valid_prices >= 5000) & (valid_prices < 10000)).sum()),
        '$10k+': int((valid_prices >= 10000).sum())
    }

    return distribution


def generate_latest_listings():
    file_path = get_latest_data_file()
    if not file_path:
        return None

    df = pd.read_csv(file_path)

    df['Price_Clean'] = df['Price'].apply(clean_price)
    df['Mileage_Clean'] = df['Mileage'].apply(clean_mileage)

    stats = {
        'total': int(len(df)),
        'avg_price': float(round(df['Price_Clean'].mean(), 2)) if df['Price_Clean'].notna().any() else 0,
        'registered': int(len(df[df['Registration Status'] == 'Yes'])),
        'file_date': file_path.stem.replace('car_data_', ''),
        'top_manufacturer': str(df['Manufacturer'].mode()[0]) if not df.empty else 'N/A'
    }

    priority_columns = ['Manufacturer', 'Model', 'Year', 'Price', 'Mileage', 'Damage description', 'Link']
    other_columns = [col for col in df.columns if col not in priority_columns and col not in ('Price_Clean', 'Mileage_Clean')]
    columns_order = priority_columns + other_columns
    display_data = df[columns_order].copy()

    # Clean up float formatting for integer columns
    integer_cols = ['Year', 'Seats', 'Keys']
    for col in integer_cols:
        if col in display_data.columns:
            display_data[col] = display_data[col].apply(lambda x: str(int(x)) if pd.notna(x) and str(x).replace('.0','').isdigit() else (str(x) if pd.notna(x) else ''))

    listings = []
    for _, row in display_data.iterrows():
        listing = {}
        for col in columns_order:
            listing[col] = str(row[col]) if pd.notna(row[col]) else ''
        listings.append(listing)

    return {'stats': stats, 'columns': columns_order, 'listings': listings, 'count': len(listings)}


def main():
    print("=" * 60)
    print("Generating API JSON files for static hosting")
    print("=" * 60)

    os.makedirs(DATA_API_DIR, exist_ok=True)

    # Overview
    print("\n[1/6] Generating overview stats...")
    overview = generate_overview()
    if overview:
        with open(DATA_API_DIR / "overview.json", "w") as f:
            json.dump(overview, f)
        print(f"  ✓ {len(overview['top_manufacturers'])} manufacturers, {overview['total_listings']:,} listings")

    # Price trends
    print("[2/6] Generating price trends...")
    trends = generate_price_trends()
    if trends:
        with open(DATA_API_DIR / "price_trends.json", "w") as f:
            json.dump(trends, f)
        print(f"  ✓ {len(trends)} data points (sampled weekly)")

    # Manufacturers
    print("[3/6] Generating manufacturer analysis...")
    manufacturers = generate_manufacturers()
    if manufacturers:
        with open(DATA_API_DIR / "manufacturers.json", "w") as f:
            json.dump(manufacturers, f)
        print(f"  ✓ Top {len(manufacturers)} manufacturers")

    # Damage analysis
    print("[4/6] Generating damage analysis...")
    damage = generate_damage_analysis()
    if damage:
        with open(DATA_API_DIR / "damage_analysis.json", "w") as f:
            json.dump(damage, f)
        print(f"  ✓ {len(damage)} damage types")

    # Price distribution
    print("[5/6] Generating price distribution...")
    distribution = generate_price_distribution()
    if distribution:
        with open(DATA_API_DIR / "price_distribution.json", "w") as f:
            json.dump(distribution, f)
        print(f"  ✓ {len(distribution)} price buckets")

    # Latest listings
    print("[6/6] Generating latest listings...")
    latest = generate_latest_listings()
    if latest:
        with open(DATA_API_DIR / "latest_listings.json", "w") as f:
            json.dump(latest, f, default=str)
        print(f"  ✓ {latest['count']} listings from {latest['stats']['file_date']}")

    print(f"\n✅ All API JSON files saved to {DATA_API_DIR.resolve()}")
    print("Commit these files and deploy to Netlify.")


if __name__ == '__main__':
    main()
