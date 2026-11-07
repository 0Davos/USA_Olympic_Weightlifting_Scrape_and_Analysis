-- One-time security setup for the Supabase database. RUN THIS YOURSELF in the Supabase dashboard
-- (SQL Editor). No script in this repo runs it, and the password must never be committed.
--
-- WHY
--   1. Supabase turns every table in the `public` schema into a REST API that anyone holding the project's
--      public "anon" key can call. meet_results currently has row-level security OFF and full privileges
--      (INSERT/UPDATE/DELETE/TRUNCATE) for the `anon` and `authenticated` roles, so anyone with that key
--      could change or wipe it - no database password needed. The website never uses that API, so this
--      locks it shut.
--   2. The website's API only ever reads meet_results, but it would otherwise connect with the full
--      `postgres` login the data pipeline uses. If that connection string leaked, anyone could modify
--      everything. A read-only role limits the damage to "can read public results".
--
-- BEFORE RUNNING: replace CHANGE_ME with a long random password, in the editor only (don't save it here).
--
-- AFTER RUNNING
--   * Build the website's connection string from the Session Pooler URI in Dashboard -> Connect, but with
--     the user `website_reader.<your-project-ref>` (through the pooler a role name carries the project ref,
--     like `postgres.<ref>`) and the new password.
--   * Put that string in Vercel as SUPABASE_DB_URL. Keep the original `postgres` string only in the GitHub
--     Actions secret and your local .env - the pipeline needs it to load data.
--   * Also worth switching off the REST API entirely if you don't use it (Dashboard -> Settings -> Data API).
--
-- The pipeline connects as `postgres`, the table owner, which bypasses row-level security, so none of this
-- affects loading data. TRUNCATE (used on every reload) keeps privileges and policies; if meet_results is
-- ever dropped and recreated, run this file again.

-- 1. Lock the table against Supabase's public roles
ALTER TABLE public.meet_results ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.meet_results FROM anon, authenticated;

-- 2. A read-only login for the website
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'website_reader') THEN
    CREATE ROLE website_reader WITH LOGIN PASSWORD 'CHANGE_ME' NOSUPERUSER NOCREATEDB NOCREATEROLE;
  END IF;
END
$$;

GRANT USAGE ON SCHEMA public TO website_reader;
GRANT SELECT ON public.meet_results TO website_reader;

-- Row-level security is on, so a non-owner needs a policy before it can read anything.
DROP POLICY IF EXISTS website_reader_select ON public.meet_results;
CREATE POLICY website_reader_select ON public.meet_results FOR SELECT TO website_reader USING (true);

-- A runaway query shouldn't hold a connection for long (the API also sets its own 5s limit)
ALTER ROLE website_reader SET statement_timeout = '10s';
