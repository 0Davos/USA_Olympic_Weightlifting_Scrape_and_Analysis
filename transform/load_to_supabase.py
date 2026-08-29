# Loads the display-relevant subset of meet_results_FEATURES.csv into Supabase
# for the website to query. Full replace each run (TRUNCATE + reload) rather
# than incremental - the pipeline already does a full rebuild each run, and the
# data is small enough (~35MB) that a full reload is cheap.

import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_FEATURES.csv")

TABLE_NAME = "meet_results"

# CSV column -> Supabase column. Renamed to clean SQL identifiers (lowercase,
# underscores, no spaces/special characters) so future queries don't need to
# quote every identifier. performance_percentile is deliberately excluded -
# it's derived from internal, non-official weight-class bins used for
# modeling/analysis, not something the website should present as-is.
COLUMN_MAP = {
    "Meet": "meet",
    "Date": "date",
    "Weight Category": "weight_category",
    "Name": "name",
    "Bodyweight": "bodyweight",
    "Sn#1": "sn_1",
    "Sn#2": "sn_2",
    "Sn#3": "sn_3",
    "CJ#1": "cj_1",
    "CJ#2": "cj_2",
    "CJ#3": "cj_3",
    "Best Sn": "best_sn",
    "Best CJ": "best_cj",
    "Total": "total",
    "Age Group": "age_group",
    "Gender": "gender",
    "weight_class": "weight_class",
}


def load_to_supabase():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return

    df = pd.read_csv(FEATURES_CSV_PATH)
    df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)

    engine = create_engine(db_url)
    with engine.begin() as conn:
        conn.execute(text(f'TRUNCATE TABLE "{TABLE_NAME}"'))
        df.to_sql(TABLE_NAME, conn, if_exists='append', index=False, method='multi', chunksize=5000)

    print(f"Loaded {len(df)} rows into Supabase table '{TABLE_NAME}'")


if __name__ == '__main__':
    load_dotenv()
    load_to_supabase()
