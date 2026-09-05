-- Idempotent migration for chk_member_moniker_format.
--
-- Loads as part of checkmember_moniker_format which runs every startup.
-- The DO block is a no-op when the constraint already permits namespaced
-- monikers; on legacy DBs (constraint still flat-form) it drops and
-- recreates with the namespaced pattern.

do $$
begin
  if exists (
    select 1 from pg_constraint
    where conname = 'chk_member_moniker_format'
      and pg_get_constraintdef(oid) like '%^[a-zA-Z0-9_]+$%'
  ) then
    alter table engine.__member drop constraint chk_member_moniker_format;
    alter table engine.__member
      add constraint chk_member_moniker_format
      check (moniker ~ '^[a-zA-Z0-9_]+(?::[a-zA-Z0-9_]+)?$');
  end if;
end
$$;
