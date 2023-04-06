\echo map_sigop_sigpath
create table if not exists engine.map_sigop_sigpath (
    "memberid" bigint constraint fk_engine_sigop_memberid references engine.__member(id) on update cascade on delete cascade,
    "sigpath" ltree constraint fk_engine_sigop_sigpath references engine.__sig(path) on update cascade on delete cascade,
    "createdbyid" bigint constraint fk_map_sig_sigop_createdbyid references engine.__member(id) on update cascade on delete set null,
    "datecreated" timestamptz,
    "approvedbyid" bigint constraint fk_map_sig_sigop_approvedbyid references engine.__member(id) on update cascade on delete set null,
    "dateapproved" timestamptz
);

create unique index if not exists idx_map_sigop_sigpath on engine.map_sigop_sigpath(memberid, sigpathpattern);
