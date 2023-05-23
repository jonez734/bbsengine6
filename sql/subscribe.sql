create table if not exists engine.subscribe_blurb (
    memberid bigint constraint fk_subscribe_blurb_memberid references engine.__member(id) on update cascade on delete cascade,
    blurbid bigint constraint fk_subscribe_blurb_blurbid references engine.__blurb(id) on update cascade on delete cascade
);

create unique index idx_subscribe_blurb on engine.subscribe_blurb(memberid, blurbid);

create table if not exists engine.subscribe_sig (
    memberid bigint constraint fk_subscribe_sig_memberid references engine.__member(id) on update cascade on delete cascade,
    sigpath ltree constraint fk_subscribe_sig_sigpath references engine.__sig(path) on update cascade on delete cascade
);

create unique index idx_subscribe_sig on engine.subscribe_sig(memberid, sigpath);
