-- migrate_notify_to_message.sql
-- Data migration script: copy legacy notify tables into unified message tables.
--
-- Run this AFTER checkmessage.py has installed the message tables.
-- The script is idempotent (uses ON CONFLICT DO NOTHING where possible).
--
-- Mapping:
--   __notify.notification_type -> __message.channel
--   __notify.template + vars  -> __message.template + template_vars
--   __notify.rendered_message -> __message.content
--   __notify.urgency          -> __message.urgency
--   __notify.sender_moniker   -> __message.sender_moniker
--   __notify.datecreated      -> __message.datestamp
--
--   __notify_recipient.recipient_moniker -> __message_recipient.recipient_moniker
--   __notify_recipient.status (read/delivered) -> __message_recipient.status
--   __notify_recipient.dateread/datedelivered  -> __message_recipient.dateread/datedelivered
--
--   __notify_block.blocker/blocked -> __message_block.blocker/blocked
--   __notify_group.group_name + member_moniker -> __message_group + __message_group_member
--   __notify_type.* -> __message_type.* (channel name = type_name)
--
-- After successful migration, the legacy tables can be archived or dropped.

-- 1. Migrate notify types -> message types
INSERT INTO engine.__message_type (type_name, description, rate_limit_per_hour, requires_approval, datemodified)
SELECT
    type_name,
    description,
    rate_limit_per_hour,
    requires_approval,
    datemodified
FROM engine.__notify_type
ON CONFLICT (type_name) DO NOTHING;

-- 2. Migrate groups: __notify_group uses (group_name, member_moniker) in one table.
--    __message normalizes to __message_group + __message_group_member.
INSERT INTO engine.__message_group (name, description, createdby, datecreated)
SELECT DISTINCT group_name, NULL, createdby, datecreated
FROM engine.__notify_group
ON CONFLICT (name) DO NOTHING;

INSERT INTO engine.__message_group_member (group_id, member_moniker, addedby, dateadded)
SELECT g.id, ng.member_moniker, ng.addedby, ng.dateadded
FROM engine.__notify_group ng
JOIN engine.__message_group g ON g.name = ng.group_name
ON CONFLICT (group_id, member_moniker) DO NOTHING;

-- 3. Migrate blocks
INSERT INTO engine.__message_block (blocker_moniker, blocked_moniker, datereviewed)
SELECT blocker_moniker, sender_moniker, datecreated
FROM engine.__notify_block
ON CONFLICT (blocker_moniker, blocked_moniker) DO NOTHING;

-- 4. Migrate messages
-- Map notification_type -> channel. If the type was deleted from __notify_type
-- the legacy notification_type text becomes the channel.
INSERT INTO engine.__message (id, channel, sender_moniker, content, data, urgency, template, template_vars, datestamp)
SELECT
    n.id,
    COALESCE(n.notification_type, 'migrated'),
    n.sender_moniker,
    COALESCE(n.rendered_message, ''),
    n.data,
    COALESCE(n.urgency, 'ROUTINE'::engine.notify_urgency_enum),
    n.template,
    n.template_vars,
    n.datecreated
FROM engine.__notify n
ON CONFLICT (id) DO NOTHING;

-- Update the sequence so future message IDs don't collide with migrated ones
SELECT setval(
    pg_get_serial_sequence('engine.__message', 'id'),
    GREATEST(
        COALESCE((SELECT MAX(id) FROM engine.__message), 0),
        COALESCE((SELECT MAX(id) FROM engine.__notify), 0)
    )
);

-- 5. Migrate recipients
INSERT INTO engine.__message_recipient (message_id, recipient_moniker, status, datedelivered, dateread)
SELECT
    nr.notify_id,
    nr.recipient_moniker,
    CASE
        WHEN nr.dateread IS NOT NULL THEN 'read'
        WHEN nr.datedelivered IS NOT NULL THEN 'delivered'
        ELSE 'pending'
    END,
    nr.datedelivered,
    nr.dateread
FROM engine.__notify_recipient nr
ON CONFLICT (message_id, recipient_moniker) DO NOTHING;
