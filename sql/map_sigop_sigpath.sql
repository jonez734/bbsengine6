\echo map_sigop_sigpath
create table if not exists engine.map_sigop_sigpath (
    "membermoniker" text constraint fk_engine_sigop_membermoniker references engine.__member(moniker) on update cascade on delete cascade,
    "sigpath" ltree constraint fk_engine_sigop_sigpath references engine.__sig(path) on update cascade on delete cascade,
    "createdbymoniker" bigint constraint fk_map_sig_sigop_createdbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz,
    "approvedbymoniker" bigint constraint fk_map_sig_sigop_approvedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "dateapproved" timestamptz
);

create unique index if not exists idx_map_sigop_sigpath on engine.map_sigop_sigpath(memberid, sigpathpattern);
