--\echo channel.sql
-- Announce-Only Channels (Phase: Channel Access Control)
--
-- Channels are named pub/sub topics. The "announce_only" flag restricts
-- publishing to a configured list of announcers (plus sysops by default).
-- Anyone may still subscribe and read.

create table engine.__channel (
    "id" bigserial unique not null primary key,
    "name" text not null unique,
    "description" text,
    "announce_only" boolean not null default false,
    "createdby" citext constraint fk_channel_createdby
        references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz default now(),
    "datemodified" timestamptz default now()
);

create index idx_engine_channel_name on engine.__channel(name);
create index idx_engine_channel_announce_only on engine.__channel(announce_only)
    where announce_only = true;

-- Map of explicit announcers per channel. Sysops are always allowed
-- (enforced in code, not stored here).
create table engine.__channel_announcer (
    "id" bigserial unique not null primary key,
    "channel_id" bigint not null constraint fk_channel_announcer_channel
        references engine.__channel(id) on update cascade on delete cascade,
    "moniker" citext not null constraint fk_channel_announcer_moniker
        references engine.__member(moniker) on update cascade on delete cascade,
    "addedby" citext constraint fk_channel_announcer_addedby
        references engine.__member(moniker) on update cascade on delete set null,
    "dateadded" timestamptz default now(),
    unique(channel_id, moniker)
);

create index idx_engine_channel_announcer_channel on engine.__channel_announcer(channel_id);
create index idx_engine_channel_announcer_moniker on engine.__channel_announcer(moniker);

-- View that exposes announce_only alongside an array of announcer monikers
-- for convenient permission checks.
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
            (
                select array_agg(a.moniker order by a.moniker)
                from engine.__channel_announcer a
                where a.channel_id = c.id
            ),
            '{}'::citext[]
        ) as announcers
    from engine.__channel c;

-- Grants
grant all on engine.__channel to web, sysop, term;
grant all on engine.__channel_id_seq to web, sysop, term;
grant all on engine.__channel_announcer to web, sysop, term;
grant all on engine.__channel_announcer_id_seq to web, sysop, term;
grant select on engine.channel to web, term, sysop, member;
