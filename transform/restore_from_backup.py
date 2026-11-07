# Manual disaster-recovery tool: puts the one-run-behind backup (meet_results_backup, written by
# load_to_supabase.py right before each reload) back into the live meet_results table.
#
# It is a dry run by default - it only reports what it would do. Pass --confirm to really restore:
#     python transform/restore_from_backup.py              # look first
#     python transform/restore_from_backup.py --confirm    # do it
#
# The restore is a single transaction (truncate the live table, copy the backup back, check the row
# count), so it either completes or changes nothing. Uses SUPABASE_DB_URL from the environment/.env,
# like load_to_supabase.py.

import sys

from dotenv import load_dotenv
import os
from sqlalchemy import create_engine, text

from load_to_supabase import BACKUP_TABLE_NAME, TABLE_NAME


def _columns(conn, table):
    """A table's column names in order. Looked up through the search path, so it also finds temp tables."""
    rows = conn.execute(
        text("SELECT attname FROM pg_attribute WHERE attrelid = to_regclass(:t) AND attnum > 0 "
             "AND NOT attisdropped ORDER BY attnum"),
        {"t": f'"{table}"'},
    )
    return [r[0] for r in rows]


def restore_backup(conn, confirm=False, table=TABLE_NAME, backup=BACKUP_TABLE_NAME):
    """Restores `table` from `backup`. Returns the number of rows restored, or None for a dry run.
    Raises RuntimeError (and so rolls the transaction back) if there is nothing safe to restore."""
    if conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f'"{backup}"'}).scalar() is False:
        raise RuntimeError(f"There is no '{backup}' table - nothing to restore from.")
    backup_rows = conn.execute(text(f'SELECT count(*) FROM "{backup}"')).scalar()
    live_rows = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
    if not backup_rows:
        raise RuntimeError(f"'{backup}' is empty - refusing to replace '{table}' with nothing.")

    live_cols, backup_cols = _columns(conn, table), set(_columns(conn, backup))
    shared = [c for c in live_cols if c in backup_cols]
    missing = [c for c in live_cols if c not in backup_cols]
    print(f"live '{table}': {live_rows} rows | backup '{backup}': {backup_rows} rows")
    print(f"columns copied: {len(shared)}" + (f" | not in the backup (will be NULL): {missing}" if missing else ""))

    if not confirm:
        print("Dry run: nothing was changed. Re-run with --confirm to restore.")
        return None

    column_list = ", ".join(f'"{c}"' for c in shared)
    conn.execute(text(f'TRUNCATE TABLE "{table}"'))
    conn.execute(text(f'INSERT INTO "{table}" ({column_list}) SELECT {column_list} FROM "{backup}"'))
    restored = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
    if restored != backup_rows:
        raise RuntimeError(f"Row count mismatch after restore ({restored} vs {backup_rows}) - rolled back.")
    print(f"Restored {restored} rows into '{table}'.")
    return restored


def main():
    load_dotenv()
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL not found in environment variables")
        return 1
    try:
        with create_engine(db_url).begin() as conn:
            restore_backup(conn, confirm="--confirm" in sys.argv)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
