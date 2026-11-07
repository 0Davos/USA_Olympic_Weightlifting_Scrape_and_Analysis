"""Checks the backup step in transform/load_to_supabase.py and the restore tool in
transform/restore_from_backup.py against the live Supabase database, using ONLY temporary tables.

The temp tables are built from a 500-row sample of the real meet_results table and exist only for this
connection (they vanish when it closes). The real tables are only read: the script records meet_results'
row count before and after and confirms meet_results_backup was never created.

Needs SUPABASE_DB_URL in the repo-root .env and network access. Run from the repo root:
    python tests/check_backup_restore.py
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "transform"))
load_dotenv(ROOT / ".env")

import load_to_supabase as L  # noqa: E402
import restore_from_backup as R  # noqa: E402

failures = []


def check(label, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + label + (f"   [{detail}]" if detail else ""))
    if not ok:
        failures.append(label)


engine = create_engine(os.environ["SUPABASE_DB_URL"])
for _ in range(3):
    try:
        conn = engine.connect()
        break
    except Exception as e:
        print("connect failed, retrying:", str(e).splitlines()[0][:60])
        time.sleep(3)
else:
    raise SystemExit("could not reach the database - check SUPABASE_DB_URL and your network")


def n(table):
    return conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()


def exists(name):
    return conn.execute(text("SELECT to_regclass(:t) IS NOT NULL"), {"t": f'public."{name}"'}).scalar()


def same_rows(a, b):
    q = lambda x, y: conn.execute(text(f'SELECT count(*) FROM (SELECT * FROM "{x}" EXCEPT SELECT * FROM "{y}") t')).scalar()
    return q(a, b) == 0 and q(b, a) == 0


real_before = n("meet_results")
print(f"real meet_results rows before: {real_before} | real backup table exists before: {exists(L.BACKUP_TABLE_NAME)}\n")

conn.rollback()  # end the transaction SQLAlchemy auto-started for the reads above
trans = conn.begin()
try:
    conn.execute(text("CREATE TEMP TABLE t_live AS SELECT * FROM public.meet_results ORDER BY id LIMIT 500"))
    conn.execute(text("CREATE TEMP TABLE t_empty AS SELECT * FROM public.meet_results WHERE false"))

    # ---- backup
    got = L.backup_live_table(conn, "t_live", "t_backup")
    check("backup copies every live row", got == 500 and n("t_backup") == 500 and same_rows("t_live", "t_backup"))
    rls = conn.execute(text("SELECT relrowsecurity FROM pg_class WHERE oid = to_regclass('\"t_backup\"')")).scalar()
    check("the backup table has row-level security on (so Supabase's public roles can't touch it)", rls is True)
    got = L.backup_live_table(conn, "t_empty", "t_backup")
    check("an EMPTY live table does not overwrite the backup", got is None and n("t_backup") == 500)
    conn.execute(text("DELETE FROM t_live WHERE id IN (SELECT id FROM t_live ORDER BY id LIMIT 50)"))
    got = L.backup_live_table(conn, "t_live", "t_backup")
    check("a second backup replaces the first (450 rows now)", got == 450 and n("t_backup") == 450)

    # ---- restore: a dry run changes nothing
    conn.execute(text("DELETE FROM t_live WHERE id IN (SELECT id FROM t_live ORDER BY id LIMIT 100)"))
    before = n("t_live")
    res = R.restore_backup(conn, confirm=False, table="t_live", backup="t_backup")
    check("dry run reports and changes nothing", res is None and n("t_live") == before == 350)

    # ---- restore: the real thing
    res = R.restore_backup(conn, confirm=True, table="t_live", backup="t_backup")
    check("--confirm restores every backup row, identical content (ids included)",
          res == 450 and n("t_live") == 450 and same_rows("t_live", "t_backup"))

    # ---- refusals leave the live table alone
    for label, kwargs in [("missing backup table", dict(backup="t_does_not_exist")), ("empty backup", dict(backup="t_empty"))]:
        sp = conn.begin_nested()
        try:
            R.restore_backup(conn, confirm=True, table="t_live", **kwargs)
            check(f"refuses a {label}", False, "no error raised")
        except RuntimeError as e:
            check(f"refuses a {label}", True, str(e)[:60])
        finally:
            sp.rollback()
        check(f"   ...and live is untouched after the {label} refusal", n("t_live") == 450)

    # ---- an older backup lacking a newer column (e.g. bombed_out) still restores the rest
    conn.execute(text("CREATE TEMP TABLE t_old AS SELECT id, meet, date, weight_category, name, bodyweight, sn_1, sn_2, sn_3, "
                      "cj_1, cj_2, cj_3, best_sn, best_cj, total, age_group, gender, weight_class FROM t_live"))
    conn.execute(text("UPDATE t_live SET bombed_out = true"))
    res = R.restore_backup(conn, confirm=True, table="t_live", backup="t_old")
    nulls = conn.execute(text("SELECT count(*) FROM t_live WHERE bombed_out IS NULL")).scalar()
    check("an old backup without bombed_out restores the other columns (bombed_out -> NULL)", res == 450 and nulls == 450)
finally:
    trans.rollback()  # nothing above persists; temp tables vanish with the connection anyway

conn.close()
conn = engine.connect()
real_after = n("meet_results")
check("REAL meet_results row count unchanged", real_after == real_before, f"{real_before} -> {real_after}")
check(f"REAL {L.BACKUP_TABLE_NAME} table was never created by this script", exists(L.BACKUP_TABLE_NAME) is False)
conn.close()

print("\n" + (f"{len(failures)} FAILED: {failures}" if failures else "ALL PASSED"))
sys.exit(1 if failures else 0)
