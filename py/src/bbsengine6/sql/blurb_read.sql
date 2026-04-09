--\echo map_member_blurb_read

create table if not exists engine.map_member_blurb_read (
    moniker citext references engine.__member(moniker) on delete cascade,
    blurbid bigint references engine.__blurb(id) on delete cascade,
    dateread timestamptz default now(),
    primary key (moniker, blurbid)
);

create index if not exists idx_member_blurb_read_moniker on engine.map_member_blurb_read (moniker);
create index if not exists idx_member_blurb_read_blurbid on engine.map_member_blurb_read (blurbid);

grant select on engine.map_member_blurb_read to web;
grant insert, delete on engine.map_member_blurb_read to term;