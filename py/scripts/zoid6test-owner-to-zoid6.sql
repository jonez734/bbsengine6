-- Make every user object in zoid6test owned by role zoid6.
--
-- Run as jam (superuser, or the database owner with rights to change ownership).
-- Ownership stays with zoid6 (the app role). The test role opencode is then made a
-- member of zoid6 so it inherits access.
--
-- Scope: zoid6test only. public (owned by pg_database_owner) is left as is.
--
-- Usage:  psql -h /var/run/postgresql -U jam -d zoid6test -v ON_ERROR_STOP=1 -f <this file>

BEGIN;

-- 1. Schemas.
ALTER SCHEMA engine OWNER TO zoid6;
ALTER SCHEMA bank   OWNER TO zoid6;
ALTER SCHEMA casino OWNER TO zoid6;  -- already zoid6; no-op

-- 2. Relations (tables, views, matviews, sequences, partitioned tables, foreign tables).
--    Sequences linked to a table (serial/identity) are skipped: they follow the table.
DO $$
DECLARE r record; kind text;
BEGIN
  FOR r IN
    SELECT n.nspname, c.relname, c.relkind
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname IN ('engine','bank','casino')
      AND c.relkind IN ('r','v','m','S','p','f')
      AND pg_get_userbyid(c.relowner) <> 'zoid6'
      AND NOT (c.relkind = 'S' AND EXISTS (
            SELECT 1 FROM pg_depend d
            WHERE d.objid = c.oid AND d.deptype IN ('a','i')))
  LOOP
    kind := CASE r.relkind
              WHEN 'v' THEN 'VIEW'
              WHEN 'm' THEN 'MATERIALIZED VIEW'
              WHEN 'S' THEN 'SEQUENCE'
              WHEN 'f' THEN 'FOREIGN TABLE'
              ELSE 'TABLE' END;
    EXECUTE format('ALTER %s %I.%I OWNER TO zoid6', kind, r.nspname, r.relname);
  END LOOP;
END $$;

-- 3. Functions and procedures in the app schemas. SECURITY DEFINER functions are already
--    owned by zoid6 (checked: 28 of 28). public is skipped: its functions belong to the
--    ltree extension, which must stay with its owner.
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT p.oid::regprocedure AS sig, p.prokind
    FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname IN ('engine','bank','casino')
      AND pg_get_userbyid(p.proowner) <> 'zoid6'
      AND NOT EXISTS (SELECT 1 FROM pg_depend d
                      WHERE d.objid = p.oid AND d.deptype = 'e')  -- extension-owned
  LOOP
    EXECUTE format('ALTER %s %s OWNER TO zoid6',
      CASE r.prokind WHEN 'p' THEN 'PROCEDURE' ELSE 'FUNCTION' END, r.sig);
  END LOOP;
END $$;

-- 4. Types (enums, composites, domains) in the app schemas.
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT n.nspname, t.typname, t.typtype
    FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
    WHERE n.nspname IN ('engine','bank','casino')
      AND t.typtype IN ('e','d','c')
      AND t.typrelid = 0            -- composite types of tables are owned by the table
      AND pg_get_userbyid(t.typowner) <> 'zoid6'
  LOOP
    EXECUTE format('ALTER %s %I.%I OWNER TO zoid6',
      CASE r.typtype WHEN 'd' THEN 'DOMAIN' ELSE 'TYPE' END, r.nspname, r.typname);
  END LOOP;
END $$;

-- 5. Give opencode access through membership in zoid6 (not ownership).
GRANT zoid6 TO opencode;

COMMIT;
