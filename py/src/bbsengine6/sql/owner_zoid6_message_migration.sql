-- Move ownership of the engine message objects from jam to the zoid6 owner role.
--
-- Convention: zoid6 owns the install objects. The bed role is the runtime login
-- only and owns nothing. The zoid6-owned SECURITY DEFINER read functions can
-- only reach these relations when zoid6 owns them.
--
-- Run once, as a superuser or as the current owner, against the install database.
-- Idempotent: ALTER ... OWNER TO is a no-op when the owner already matches.
-- Requires the zoid6 role to exist (checkzoid6role creates it).

begin;

-- tables and views
alter table engine.__message owner to zoid6;
alter table engine.__message_block owner to zoid6;
alter table engine.__message_group owner to zoid6;
alter table engine.__message_group_member owner to zoid6;
alter table engine.__message_rate_limit owner to zoid6;
alter table engine.__message_recipient owner to zoid6;
alter table engine.__message_source owner to zoid6;
alter table engine.__message_type owner to zoid6;
alter view engine.message owner to zoid6;
alter view engine.message_blocked owner to zoid6;
alter view engine.message_unread owner to zoid6;
alter view engine.message_urgent owner to zoid6;

-- sequences
alter sequence engine.__message_block_id_seq owner to zoid6;
alter sequence engine.__message_group_id_seq owner to zoid6;
alter sequence engine.__message_group_member_id_seq owner to zoid6;
alter sequence engine.__message_id_seq owner to zoid6;
alter sequence engine.__message_rate_limit_id_seq owner to zoid6;
alter sequence engine.__message_recipient_id_seq owner to zoid6;
alter sequence engine.__message_type_id_seq owner to zoid6;

commit;
