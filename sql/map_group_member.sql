\echo map_group_member
create table if not exists engine.map_group_member (
    "memberid" bigint constraint fk_engine_group_memberid references engine.__member(id) on update cascade on delete cascade,
    "groupname" text constraint fk_engine_group_name references engine.__group(name) on update cascade on delete cascade,
    "isadmin" boolean default 'f'
);

create unique index if not exists idx_engine_group_member on engine.map_group_member (memberid, groupname);
