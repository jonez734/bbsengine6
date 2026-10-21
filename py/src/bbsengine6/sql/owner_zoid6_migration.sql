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

-- trigger function created by sql/message.sql (engine schema, zoid6-owned schema)
alter function engine.__message_recipient_notify() owner to zoid6;

commit;
