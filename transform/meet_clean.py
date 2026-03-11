# Cleaning meet_results.csv

import pandas as pd
import re

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

    cat = re.sub(r'\+(\d+)\s*kg', r'\1+kg', cat) # Convert "+##kg" to "##+kg" for uniformity

    return cat


def parse_weight_category(cat):
    cat = str(cat).strip()

    # Extract bodyweight class (e.g., '81kg', '+87kg', '65+kg')
    pattern = r'^(Masters \(\d{2}(?:-\d{2}|\+)\)|\d{1,2}(?:-\d{2})? Under Age Group(?: \+?\d+ Kg)?|Open \+?\d+ Kg|Junior \+?\d+ Kg)$'
    # pattern replacing r'(\+?\d+\s*\+?kg)'
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
    # Remove gender terms to isolate age group or division label
    age_group = base.replace("Women's", '').replace("Men's", '').strip()
    age_group = re.sub(r'\s+', ' ', age_group).strip()

    return pd.Series([age_group, gender, bw])




if __name__ == '__main__':
    df = pd.read_csv("meet_results.csv")


    df['Weight Category'] = (
    df['Weight Category']
      .astype(str)
      .str.strip()
      .str.replace('\xa0', ' ', regex=False)
      .str.replace('\u200b', '', regex=False)
      .str.replace('\ufeff', '', regex=False)  # remove BOM
      .apply(lambda x: re.sub(r'\s+', ' ', x))  # collapse any kind of whitespace to a single space
    )
    #df['Weight Category'] = df['Weight Category'].astype(str).str.strip()
    #df['Weight Category'] = df['Weight Category'].str.replace('\xa0', ' ', regex=False)  # replace non-breaking space
    #df['Weight Category'] = df['Weight Category'].str.replace('\u200b', '', regex=False)  # remove zero-width space

    df['Weight Category'] = df['Weight Category'].apply(clean_category)
    df[['WC_AgeGroup', 'WC_Gender', 'WC_BW']] = df['Weight Category'].apply(parse_weight_category)
    
    print(df["WC_AgeGroup"].unique())
    df.to_csv("meet_results_CLEANED.csv", index=False)