grant select on engine.member to web, term;
grant select,update,delete on engine.flag to web, term;
grant insert on engine.flag to :sysop;
grant select on engine.sig to web, term;
grant usage on schema engine to web, term;
grant update,delete on engine.__sig to web, term;
grant select,update,delete on engine.map_member_flag to web, term;
grant select,update,delete on engine.map_memberid_inetaddr to web, term;
grant usage on schema engine to web, term;
