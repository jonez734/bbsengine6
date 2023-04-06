create table if not exists engine.subscribe_node (
    memberid bigint constraint fk_subscribe_node_memberid references engine.__member(id) on update cascade on delete cascade,
    nodeid bigint constraint fk_subscribe_node_nodeid references engine.__node(id) on update cascade on delete cascade
);

create unique index idx_subscribe_node on engine.subscribe_node(memberid, nodeid);

create table if not exists engine.subscribe_sig (
    memberid bigint constraint fk_subscribe_sig_memberid references engine.__member(id) on update cascade on delete cascade,
    sigpath ltree constraint fk_subscribe_sig_sigpath references engine.__sig(path) on update cascade on delete cascade
);

create unique index idx_subscribe_sig on engine.subscribe_sig(memberid, sigpath);
