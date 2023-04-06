\echo map_sig_moderator
create or replace table engine.map_sig_moderator (
    sigpath ltree constraint fk_map_sig_moderator_sigpath references engine.sig(path) on update cascade on delete cascade,
    memberid bigint constraint fk_map_sig_moderator_memberid references engine.__member(id) on update cascade on delete cascade,
    datecreated timestamptz,
    createdbyid bigint constraint fk_map_sig_moderator_createdbyid references engine.__member(id) on update cascade on delete set null,
    dateapproved timestamptz,
    approvedbyid bigint constraint fk_map_sig_moderator_approvedbyid references engine.__member(id) on update cascade on delete set null
);

create unique index if not exists idx_map_sig_moderator on engine.map_sig_moderator (memberid, sigpath);
