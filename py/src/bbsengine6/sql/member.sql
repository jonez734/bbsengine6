--\echo member.sql
--
-- engine.__member.password column invariant (added 2026-08-22 after the
-- 2026-08-22 auth incident): the ``password`` column MUST hold a bcrypt
-- hash with one of the recognised prefixes ``$2a$`` / ``$2b$`` / ``$2y$``
-- and length 60. NULL is allowed (member has not yet set a password) but
-- any non-NULL value must satisfy the bcrypt invariant.
--
-- Writers that MUST use ``bbsengine6.member.setpassword`` (which writes
-- ``crypt($1, gen_salt('bf'))`` server-side and produces a fresh bcrypt
-- hash on every call):
--   * console.member.add / console.member.edit
--   * bbsengine6/scripts/setpassword.py (one-shot migration tool)
--   * engine/join.php (PHP-side registration, post-port)
--
-- Writers historically known to violate this invariant (now detected at
-- auth time via ``audit_password_hash`` and blocked at write time via the
-- CHECK constraint in ``manage_password_format.sql``):
--   * Legacy PHP bbsengine under ``/srv/backups/work/zoid6/php/engine/``
--     — predates the Python port and historically used MD5-crypt
--     (``$1$...`` prefix, length 34). Any PHP migration or restore that
--     ran against this DB is the most likely source of legacy hashes.
--   * Backup/restore round-trip paths — any tool that serialises and
--     restores a member row should be either drop-and-reload (with the
--     member re-setting the password) or transparent-rehash (rare and
--     risky).
--
-- Detection / migration entry points (see ``zoid6/TODO.md`` "Password
-- column hardening — legacy MD5-crypt migration (@since 20260822)"):
--   * One-shot audit: ``bbsengine6.member.audit_password_column()``
--   * Per-auth audit: ``bbsengine6.member.audit_password_hash()``
--     (called by ``checkpassword`` on every login attempt)
--   * Constraint: ``chk_member_password_bcrypt`` in
--     ``manage_password_format.sql`` (rejects non-bcrypt writes)


create table if not exists engine.__member (
--  "id" bigserial unique not null primary key,
  "moniker" citext unique not null constraint chk_member_moniker_format check (moniker ~ '^[a-zA-Z0-9_]+$'),
  "email" text not null,
  "password" text,
  "credits" numeric(10,0),
  "parentmoniker" citext constraint fk_member_parentid references engine.__member(moniker) on update cascade on delete set null,
  "datecreated" timestamptz,
  "createdbymoniker" citext constraint fk_member_createdbyid references engine.__member(moniker) on update cascade on delete set null,
  "dateupdated" timestamptz,
  "updatedbymoniker" citext constraint fk_member_updatedbyid references engine.__member(moniker) on update cascade on delete set null,
  "approvedbymoniker" citext constraint fk_member_approvedbyid references engine.__member(moniker) on update cascade on delete set null,
  "dateapproved" timestamptz,
  "approved" boolean NOT NULL DEFAULT false,
--  "emailverified" boolean,
--  "emailverifiedbymoniker" text constraint fk_member_emailverifiedbyid references engine.__member(moniker) on update cascade on delete set null,
--  "dateemailverified" timestamptz,
--  "verifiedbymoniker" text constraint fk_member_verifiedbyid references engine.__member(moniker) on update cascade on delete set null,
--  "dateverified" timestamptz,
  "lastlogin" timestamptz,
  "lastloginfrom" inet,
  "loginid" text,
  "ui" citext,
  "tz" citext,
  "attrs" jsonb,
  "refcode" citext
);

grant select, update on engine.__member to web, term;
grant all on engine.__member to sysop;

--grant usage, select on engine.__member_id_seq to web, term;
--grant all on engine.__member_id_seq to sysop;
