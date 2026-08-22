--\echo manage_password_format.sql
--
-- engine.__member.password format invariant — reject non-bcrypt writes.
-- Added 2026-08-22 after the auth incident where a legacy $1$ MD5-crypt
-- hash survived an earlier setpassword run and defeated the bcrypt
-- round-trip in member.checkpassword.
--
-- This file is \i-included from bbsengine6.sql AFTER member.sql is loaded.
-- The constraint is created with IF NOT EXISTS so re-running bbsengine6.sql
-- on a database that already has it is a no-op.
--
-- Run AFTER the audit (bbsengine6.member.audit_password_column()) is clean:
-- the constraint will reject any future non-bcrypt INSERT or UPDATE, but it
-- will NOT retroactively fail on pre-existing bad rows (PostgreSQL CHECK
-- constraints validate on write, not on creation). The migration of
-- pre-existing rows is the operator's responsibility.

-- The constraint lives on engine.__member.password and rejects any non-NULL
-- value whose prefix is not one of the recognised bcrypt variants
-- ($2a$, $2b$, $2y$). NULL is allowed (member has not yet set a password).
--
-- Pattern: ^\$2[abxy]\$ — matches $2a$, $2b$, $2y$ (PG crypt() recognises
-- all three as bcrypt; all are length 60). The constraint does NOT
-- validate length because the prefix check is the operator-actionable
-- signal: a hash starting with $2b$ but only 30 chars long is still
-- unambiguously broken (not "a valid bcrypt of a short password").
alter table engine.__member
  drop constraint if exists chk_member_password_bcrypt;

alter table engine.__member
  add constraint chk_member_password_bcrypt
  check (password is null or password ~ '^\$2[abxy]\$');

-- Mirror the constraint onto engine.member (the view defined in
-- memberview.sql). PG CHECK constraints on the underlying table are
-- visible through the view, so this is technically redundant, but
-- listing it explicitly makes the invariant discoverable from
-- pg_constraint on either relation.
--
-- engine.member is a view, not a table, so we cannot attach a CHECK
-- constraint to it directly. The view inherits the underlying
-- engine.__member CHECK via the rewrite, so writes through the view
-- fail with the same constraint violation. The comment above is
-- documentation; no DDL is emitted for the view.

-- Inform operator-level tooling (psql \d+, bbsengine6.console.lib, future
-- CLI dashboard) that this constraint exists. PG doesn't support COMMENT
-- ON CONSTRAINT in all versions; the file comment at the top is the
-- authoritative source.
