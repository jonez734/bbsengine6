create table if not exists engine.map_membermoniker_inetaddr (
    address inet,
    hostname text,
    membermoniker citext constraint fk_engine_membermoniker_inetaddr references engine.__member(moniker) on update cascade on delete set null,
    datestamp timestamptz
);

grant all on engine.map_membermoniker_inetaddr to sysop;
grant select on engine.map_membermoniker_inetaddr to term;
