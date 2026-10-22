-- Move ownership of objects created by the bed role to the zoid6 owner role.
--
-- Convention: the install name is zoid6, so zoid6 owns the schemas and objects
-- of the zoid6 install (engine, casino, bank, postoffice). The bed role is the
-- runtime login only and must not own schema objects.
--
-- Run once, as a superuser or as the current owner, against the install database.
-- Idempotent: ALTER ... OWNER TO is a no-op when the owner already matches.
-- Requires the zoid6 role to exist (checkzoid6role creates it).

begin;

alter schema postoffice owner to zoid6;

-- tables and views
alter table postoffice.__address owner to zoid6;
alter table postoffice.__mailbox owner to zoid6;
alter table postoffice.__mailbox_address owner to zoid6;
alter table postoffice.__mailbox_member owner to zoid6;
alter table postoffice.__message owner to zoid6;
alter table postoffice.mailbox_password owner to zoid6;
alter table postoffice.member_mailbox_password owner to zoid6;
alter table postoffice.message_routing owner to zoid6;
alter table postoffice.shared_mailbox owner to zoid6;
alter table postoffice.virtual owner to zoid6;
alter view postoffice.mailbox owner to zoid6;
alter view postoffice.mailbox_address owner to zoid6;
alter view postoffice.mailbox_member owner to zoid6;

-- sequences
alter sequence postoffice.__mailbox_address_id_seq owner to zoid6;
alter sequence postoffice.__mailbox_id_seq owner to zoid6;
alter sequence postoffice.__mailbox_member_id_seq owner to zoid6;
alter sequence postoffice.member_mailbox_password_id_seq owner to zoid6;
alter sequence postoffice.message_routing_id_seq owner to zoid6;
alter sequence postoffice.shared_mailbox_id_seq owner to zoid6;

-- bank schema objects. The bed balance and transaction functions are zoid6-owned
-- SECURITY DEFINER functions, so zoid6 must own the tables they read and write.
alter table bank.__account owner to zoid6;
alter table bank.__transaction owner to zoid6;
alter table bank.__transfer owner to zoid6;
alter view bank.account owner to zoid6;
alter view bank.transaction owner to zoid6;
alter view bank.transfer owner to zoid6;
alter sequence bank.__account_id_seq owner to zoid6;
alter sequence bank.__transaction_id_seq owner to zoid6;
alter sequence bank.__transfer_id_seq owner to zoid6;

-- channel and subscribe objects (engine schema). engine.__member references
-- __channel (createdby); deleting a member runs an internal update on __channel as
-- its owner, so the owner must hold engine access.
alter table engine.__channel owner to zoid6;
alter table engine.__channel_announcer owner to zoid6;
alter view engine.channel owner to zoid6;
alter sequence engine.__channel_id_seq owner to zoid6;
alter sequence engine.__channel_announcer_id_seq owner to zoid6;

-- member table and its view. engine.member is a plain view over
-- engine.__member, so the view and the table it reads must share an owner.
alter table engine.__member owner to zoid6;
alter view engine.member owner to zoid6;

-- member flag tables (engine schema). checkmemberflag runs inside bed's
-- zoid6-owned SECURITY DEFINER wrapper, so zoid6 must own the tables it reads.
alter table engine.member_flag owner to zoid6;
alter table engine.map_member_flag owner to zoid6;

-- trigger function created by sql/message.sql (engine schema, zoid6-owned schema)
alter function engine.__message_recipient_notify() owner to zoid6;

-- catch-all: move every engine and bank table, view, sequence, and function that
-- zoid6 does not own. The explicit lines above name the known objects; this block
-- covers objects the repo does not list (found in the live catalog, 2026-10-22).
do $owner$
declare
    r record;
begin
    for r in
        select n.nspname as schema, c.relname as name, c.relkind as kind
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname in ('engine', 'bank')
          and c.relkind in ('r', 'v', 'S', 'm')
          and pg_get_userbyid(c.relowner) <> 'zoid6'
    loop
        if r.kind = 'S' then
            execute format('alter sequence %I.%I owner to zoid6', r.schema, r.name);
        elsif r.kind = 'v' then
            execute format('alter view %I.%I owner to zoid6', r.schema, r.name);
        else
            execute format('alter table %I.%I owner to zoid6', r.schema, r.name);
        end if;
    end loop;

    for r in
        select n.nspname as schema, p.proname as name, pg_get_function_identity_arguments(p.oid) as args
        from pg_proc p
        join pg_namespace n on n.oid = p.pronamespace
        where n.nspname in ('engine', 'bank')
          and pg_get_userbyid(p.proowner) <> 'zoid6'
    loop
        execute format('alter function %I.%I(%s) owner to zoid6', r.schema, r.name, r.args);
    end loop;
end
$owner$;

commit;
