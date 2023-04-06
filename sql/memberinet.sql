create table if not exists engine.map_memberid_inetaddr (
    address inet,
    hostname text,
    memberid bigint constraint fk_engine_memberid_inetaddr references engine.__member(id) on update cascade on delete set null,
    datestamp timestamptz
);
