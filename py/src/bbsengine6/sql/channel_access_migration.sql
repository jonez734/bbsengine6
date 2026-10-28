-- bbsengine6/sql/channel_access_migration.sql
-- Migration: subscribe and publish access on channels. Idempotent.
--
-- subscribe_restricted: when true, a session may subscribe only if the channel's subscribe
--   authority allows it (see ChannelService.can_subscribe). The default (false) keeps existing
--   channels open to every authenticated member.
-- publish_requires_subscription: when true, a moniker may publish only while subscribed to the
--   channel (used for chat). The default (false) keeps existing behaviour.
--
-- bed (the daemon) creates channels and reads and writes their access settings, so it needs
-- the same table privileges the web and sysop roles already have on engine.__channel.

alter table engine.__channel
    add column if not exists "subscribe_restricted" boolean not null default false;

alter table engine.__channel
    add column if not exists "publish_requires_subscription" boolean not null default false;

-- The engine.channel view keeps every existing column, in the same order and types, and adds the
-- two access flags at the end, so existing readers are unaffected.
create or replace view engine.channel as
    select
        c.id,
        c.name,
        c.description,
        c.announce_only,
        c.createdby,
        c.datecreated,
        c.datemodified,
        coalesce(
            (select array_agg(a.moniker order by a.moniker)
               from engine.__channel_announcer a
              where a.channel_id = c.id),
            '{}'::citext[]
        ) as announcers,
        c.subscribe_restricted,
        c.publish_requires_subscription
    from engine.__channel c;

grant select, insert, update, delete on engine.__channel to bed;
grant usage, select on engine.__channel_id_seq to bed;
grant select, insert, update, delete on engine.__channel_announcer to bed;
grant usage, select on engine.__channel_announcer_id_seq to bed;
grant select on engine.channel to bed;
