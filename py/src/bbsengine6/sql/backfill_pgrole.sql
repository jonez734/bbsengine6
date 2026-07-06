--\echo backfill_pgrole.sql
--
-- One-shot migration: provision engine.pgrole rows and l_<loginid>
-- PostgreSQL roles for every currently-approved member that doesn't
-- already have one.
--
-- Idempotent: skips members already in engine.pgrole. Safe to re-run.
--
-- osuser is left NULL for backfilled rows; members fill it in via
-- the [P] psql credentials console flow (see
-- py/src/bbsengine6/console/showpgrole.py).
--
-- Run as a member of the 'sysop' group (or any role that has EXECUTE
-- on engine.createpgrole).

do $$
declare
  m record;
begin
  for m in
    select mm.id, mm.loginid
      from engine.__member mm
     where engine.checkmemberflag('approved', mm.moniker) = true
       and not exists (
         select 1 from engine.pgrole pr where pr.memberid = mm.id
       )
  loop
    begin
      perform engine.createpgrole(m.loginid, null);
      raise notice 'backfill_pgrole: created role for loginid=%', m.loginid;
    exception when others then
      raise warning 'backfill_pgrole: failed for loginid=%: %', m.loginid, sqlerrm;
    end;
  end loop;
end $$;
