--\echo subscribe.sql (legacy, see LEGACY.md)
-- Legacy blurb/sig subscription tables for the bbsengine5 browse UI.
-- Not part of the new channel/pub-sub system (see channel.sql,
-- net/transport.py). Kept for backward compatibility with existing
-- consumer code that queries these tables directly. New development
-- should use the engine.__channel + engine.__channel_announcer
-- system instead.

create table if not exists engine.subscribe_blurb (
    membermoniker text constraint fk_subscribe_blurb_memberid references engine.__member(moniker) on update cascade on delete cascade,
    blurbid bigint constraint fk_subscribe_blurb_blurbid references engine.__blurb(id) on update cascade on delete cascade
);

create unique index idx_subscribe_blurb on engine.subscribe_blurb(membermoniker, blurbid);

create table if not exists engine.subscribe_sig (
    membermoniker text constraint fk_subscribe_sig_memberid references engine.__member(moniker) on update cascade on delete cascade,
    sigpath ltree constraint fk_subscribe_sig_sigpath references engine.__sig(path) on update cascade on delete cascade
);

create unique index idx_subscribe_sig on engine.subscribe_sig(membermoniker, sigpath);
