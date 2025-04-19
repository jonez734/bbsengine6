\echo map_sig_moderator
create or replace table engine.map_sig_moderator (
    sigpath ltree constraint fk_map_sig_moderator_sigpath references engine.sig(path) on update cascade on delete cascade,
    membermoniker text constraint fk_map_sig_moderator_membermoniker references engine.__member(moniker) on update cascade on delete cascade,
    datecreated timestamptz,
    createdbymoniker text constraint fk_map_sig_moderator_createdbymoniker references engine.__member(moniker) on update cascade on delete set null,
    dateapproved timestamptz,
    approvedbymoniker text constraint fk_map_sig_moderator_approvedbymoniker references engine.__member(moniker) on update cascade on delete set null
);

create unique index if not exists idx_map_sig_moderator on engine.map_sig_moderator (membermoniker, sigpath);
