# Loads the display-relevant subset of meet_results_FEATURES.csv into Supabase
# for the website to query. Full replace each run (TRUNCATE + reload) rather
# than incremental - the pipeline already does a full rebuild each run, and the
# data is small enough (~35MB) that a full reload is cheap.

import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine, text

from takedown import drop_listed, is_listed, load_hashes

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FEATURES_CSV_PATH = os.path.join(SCRIPT_DIR, "..", "data", "meet_results_FEATURES.csv")

TABLE_NAME = "meet_results"
# One-run-behind copy of the live table; transform/restore_from_backup.py puts it back by hand.
BACKUP_TABLE_NAME = "meet_results_backup"

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
    "bombed_out": "bombed_out",
    "Meet Level": "meet_level",
    "Meet Results": "meet_results",
    "Division": "division",
    "Age Bucket": "age_bucket",
}

# Columns added after the table was first created, with their SQL types. to_sql(append) won't add a
# missing column, so each is added (if missing) before the reload.
ADDED_COLUMNS = {
    "bombed_out": "boolean",
    "meet_level": "text",
    "meet_results": "integer",
    "division": "text",
    "age_bucket": "text",
}


def backup_live_table(conn, table=TABLE_NAME, backup=BACKUP_TABLE_NAME):
    """Keeps the last known-good data: the run happening at all is evidence the previous load was
    fine, so the live table is copied to the backup right before it gets replaced. Called inside the
    same transaction as the reload, so a failed reload also rolls back the backup swap and leaves
    both tables as they were. An empty live table never overwrites an existing backup.
    Returns the number of rows backed up, or None if the live table was empty."""
    live_rows = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
    if not live_rows:
        print(f"Live table is empty - leaving '{backup}' as it is")
        return None
    conn.execute(text(f'DROP TABLE IF EXISTS "{backup}"'))
    conn.execute(text(f'CREATE TABLE "{backup}" AS TABLE "{table}"'))
    # Supabase gives every new table full privileges for its public 'anon'/'authenticated' roles (the
    # REST API's roles). With row-level security on and no policies they can see and change nothing;
    # this connection is the table's owner, which bypasses it.
    conn.execute(text(f'ALTER TABLE "{backup}" ENABLE ROW LEVEL SECURITY'))
    print(f"Backed up {live_rows} rows to '{backup}'")
    return live_rows


def delete_listed_rows(conn, hashes, table):
    """Deletes takedown-listed athletes' rows from `table` (used on the backup, which is a copy of the
    previous run's data and so can still hold someone added to the list since). Names are hashed here
    in Python, the same way as everywhere else, rather than reimplemented in SQL.
    Returns the number of rows deleted."""
    if not hashes:
        return 0
    names = [r[0] for r in conn.execute(text(f'SELECT DISTINCT name FROM "{table}"'))]
    listed = [n for n in names if is_listed(n, hashes)]
    if not listed:
        return 0
    return conn.execute(text(f'DELETE FROM "{table}" WHERE name = ANY(:names)'), {"names": listed}).rowcount


def load_to_supabase():
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return

    df = pd.read_csv(FEATURES_CSV_PATH)
    df = df[list(COLUMN_MAP.keys())].rename(columns=COLUMN_MAP)
    # Read back as a float (blanks make it NaN); a whole number for the integer column.
    df["meet_results"] = df["meet_results"].astype("Int64")

    # meet_clean.py already drops takedown-listed athletes; checked again here because this is the
    # last step before the public site, and a local run could be using an older FEATURES file.
    hashes = load_hashes()
    df, n_removed = drop_listed(df, name_col="name", hashes=hashes)
    if n_removed:
        print(f"Takedown list: dropped {n_removed} rows")

    engine = create_engine(db_url)
    with engine.begin() as conn:
        # The table predates these columns; make sure each is there (no-op once it is).
        for column, sql_type in ADDED_COLUMNS.items():
            conn.execute(text(f'ALTER TABLE "{TABLE_NAME}" ADD COLUMN IF NOT EXISTS {column} {sql_type}'))

        if backup_live_table(conn) is not None:
            n_deleted = delete_listed_rows(conn, hashes, BACKUP_TABLE_NAME)
            if n_deleted:
                print(f"Takedown list: deleted {n_deleted} rows from '{BACKUP_TABLE_NAME}'")

        conn.execute(text(f'TRUNCATE TABLE "{TABLE_NAME}"'))
        df.to_sql(TABLE_NAME, conn, if_exists='append', index=False, method='multi', chunksize=5000)

    print(f"Loaded {len(df)} rows into Supabase table '{TABLE_NAME}'")


if __name__ == '__main__':
    load_dotenv()
    load_to_supabase()
