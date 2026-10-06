-- Indexes for the website's read queries (app/api/index.py). Safe to re-run.
--
-- Both endpoints match athletes on a normalized name key (trimmed, whitespace
-- collapsed, lowercased) so that spelling noise like "Nick  Bloom" / "nick bloom"
-- resolves to one athlete. The plain btree on "name" can't serve that expression,
-- so every lookup was scanning all ~325K rows. This expression index serves both
-- the prefix search (LIKE 'abc%', via text_pattern_ops) and the exact history lookup (=).
--
-- The expression must match NAME_KEY_SQL in app/api/index.py exactly, or the planner
-- won't use the index. TRUNCATE (used by transform/load_to_supabase.py) keeps indexes.

CREATE INDEX IF NOT EXISTS idx_meet_results_name_key
ON meet_results (lower(regexp_replace(btrim(name), '\s+', ' ', 'g')) text_pattern_ops);

ANALYZE meet_results;
