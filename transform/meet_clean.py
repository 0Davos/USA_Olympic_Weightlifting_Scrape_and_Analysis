# Cleaning meet_results.csv -> meet_results_CLEANED.csv

import os
import re
import numpy as np
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results.csv")
CLEANED_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_CLEANED.csv")

# Known data-entry error corrections, matched by (Name, Meet, Date) rather than row
# index, since row positions shift as new meets get appended to the raw CSV.
BODYWEIGHT_FIXES = [
    # (Name, Meet, Date, corrected_bodyweight)
    # Cross-referenced against surrounding meets for this athlete: real bodyweight is ~88.5-97
    ("Brad Alexander", "Folsom Open", "2019-05-05", 92.75),
]

# Rows where Total was recorded as exactly 400kg across wildly different bodyweights -
# a data-entry/capping glitch rather than real lifts.
SUSPICIOUS_TOTAL_400_ROWS = {
    ("2022 NAOF Qualifier", "2022-11-04", "Francisco Oliveras"),
    ("2022 NAOF Qualifier", "2022-11-04", "Julia Ryan"),
    ("2022 NAOF Qualifier", "2022-11-04", "Alec Olson"),
    ("2022 NAOF Qualifier", "2022-11-04", "Jessica Watson"),
    ("2022 NAOF Qualifier", "2022-11-04", "James Campbell"),
    ("October online qualifier", "2020-10-31", "Holly Yoon"),
    ("October online qualifier", "2020-10-31", "Daniel Yeargin"),
}


def clean_category(cat):
    if cat == "-" or pd.isna(cat):
        return None
    cat = cat.strip()  # remove leading/trailing spaces
    cat = re.sub(r'\s+', ' ', cat)  # collapse multiple spaces
    cat = re.sub(r'\s*\+\s*', '+', cat)  # remove spaces around '+'
    cat = re.sub(r'\s*kg', 'kg', cat, flags=re.IGNORECASE)  # remove spaces before kg
    cat = re.sub(r'Kg', 'kg', cat)  # lowercase 'Kg'
    cat = re.sub(r'(?<=\))(?=\d)', ' ', cat)
    cat = re.sub(r'(?<=[A-Za-z)])\+', ' +', cat)  # ensure space before '+'
    cat = re.sub(r'\s+', ' ', cat).strip()  # collapse any remaining extra spaces

    cat = re.sub(r'\+(\d+)\s*kg', r'\1+kg', cat)  # Convert "+##kg" to "##+kg" for uniformity

    return cat


def parse_weight_category(cat):
    cat = str(cat).strip()

    # Extract bodyweight class (e.g., '81kg', '+87kg', '65+kg')
    pattern = r'^(Masters \(\d{2}(?:-\d{2}|\+)\)|\d{1,2}(?:-\d{2})? Under Age Group(?: \+?\d+ Kg)?|Open \+?\d+ Kg|Junior \+?\d+ Kg)$'
    bw_match = re.search(pattern, cat, re.IGNORECASE)
    bw = bw_match.group(1) if bw_match else None

    # Remove that from the string for easier parsing
    base = cat.replace(bw, '').strip() if bw else cat

    # Determine gender
    if "Women" in base:
        gender = "Women"
    elif "Men" in base:
        gender = "Men"
    else:
        gender = None

    # Clean and identify the age group / division
    age_group = base.replace("Women's", '').replace("Men's", '').strip()
    age_group = re.sub(r'\s+', ' ', age_group).strip()

    return pd.Series([age_group, gender, bw])


def parse_mixed_format_dates(date_series):
    """Parses a Date column/Series that may contain a mix of US (M/D/YYYY) and
    ISO (YYYY-MM-DD) formatted strings - the original bulk-loaded historical
    data uses US format, while meet_scraper.py's own output uses ISO. pandas'
    default date parsing infers a single format from the whole column and
    silently fails (NaT) on whichever format doesn't match, so both are tried
    explicitly here instead."""
    parsed = pd.to_datetime(date_series, format='%m/%d/%Y', errors='coerce')
    still_missing = parsed.isna()
    parsed.loc[still_missing] = pd.to_datetime(date_series[still_missing], format='%Y-%m-%d', errors='coerce')
    return parsed


def parse_weight_categories(df):
    df['Weight Category'] = (
        df['Weight Category']
        .astype(str)
        .str.strip()
        .str.replace('\xa0', ' ', regex=False)
        .str.replace('\u200b', '', regex=False)
        .str.replace('\ufeff', '', regex=False)  # remove BOM
        .apply(lambda x: re.sub(r'\s+', ' ', x))  # collapse any kind of whitespace to a single space
    )
    df['Weight Category'] = df['Weight Category'].apply(clean_category)
    df[['WC_AgeGroup', 'WC_Gender', 'WC_BW']] = df['Weight Category'].apply(parse_weight_category)
    return df


def clean_meet_data(df):
    df = parse_weight_categories(df)

    # Drop WC_BW (redundant with Weight Category), rename to friendlier names
    df_cleaned = df.drop(columns="WC_BW")
    df_cleaned = df_cleaned.rename(columns={"WC_Gender": "Gender", "WC_AgeGroup": "Age Group"})

    df_cleaned['Date'] = parse_mixed_format_dates(df_cleaned['Date'])
    df_cleaned = df_cleaned.drop_duplicates()

    # Remove physiologically impossible outliers
    df_cleaned = df_cleaned[df_cleaned["Bodyweight"] <= 250]
    df_cleaned = df_cleaned[df_cleaned["Bodyweight"] > 0]
    df_cleaned = df_cleaned[df_cleaned["Total"] <= 400]
    df_cleaned = df_cleaned[df_cleaned["Total"] > 0]

    # Convert missed lifts (negative or zero) to NaN, preserving miss flags
    misses_to_nan_cols = ["Sn#1", "Sn#2", "Sn#3", "CJ#1", "CJ#2", "CJ#3"]
    for col in misses_to_nan_cols:
        df_cleaned[f"{col}_missed"] = df_cleaned[col] <= 0
    df_cleaned[misses_to_nan_cols] = df_cleaned[misses_to_nan_cols].apply(lambda x: x.where(x > 0, np.nan))

    # Known data-entry error corrections, matched by content (not row position)
    for name, meet, date, corrected_bw in BODYWEIGHT_FIXES:
        mask = (
            (df_cleaned["Name"] == name) &
            (df_cleaned["Meet"] == meet) &
            (df_cleaned["Date"] == pd.Timestamp(date))
        )
        df_cleaned.loc[mask, "Bodyweight"] = corrected_bw

    # Remove remaining low-bodyweight/high-total outliers
    df_cleaned = df_cleaned[
        df_cleaned["Bodyweight"].between(0, 200) &
        (df_cleaned["Total"] <= 5.5 * df_cleaned["Bodyweight"])
    ]

    # Remove known Total==400 data-entry glitches, matched by content
    row_keys = list(zip(
        df_cleaned["Meet"],
        df_cleaned["Date"].dt.strftime("%Y-%m-%d"),
        df_cleaned["Name"],
    ))
    keep_mask = [key not in SUSPICIOUS_TOTAL_400_ROWS for key in row_keys]
    df_cleaned = df_cleaned[keep_mask]

    return df_cleaned


if __name__ == '__main__':
    df = pd.read_csv(RAW_CSV_PATH)
    df_cleaned = clean_meet_data(df)

    print(df_cleaned["Age Group"].unique())
    df_cleaned.to_csv(CLEANED_CSV_PATH, index=False)
