--\echo memberview.sql
--create view engine.member as 
--  select m.*, 
--    extract(epoch from lastlogin) as lastloginepoch,
--    extract(epoch from dateupdated) as dateupdatedepoch,
--    extract(epoch from datecreated) as datecreatedepoch,
--    ( SELECT count(n.id) AS count
--           FROM engine.notify n
--          WHERE n.displayed = false AND n.memberid = m.id) AS undisplayednotifycount,
--    ( SELECT count(n.id) AS count
--           FROM engine.notify n
--          WHERE n.memberid = m.id) AS notifycount
--  from engine.__member as m
--;

create or replace view engine.member as
  select m.*,
  m.attrs->>'tier' as tier,

--  loginid,
--  shell,
--  (attributes->>'loginid')::text as loginid,
  extract(epoch from m.datecreated) as datecreatedepoch,
  extract(epoch from m.lastlogin) as lastloginepoch,
--  extract(epoch from m.dateapproved) as dateapprovedepoch,
  extract(epoch from m.dateupdated) as dateupdatedepoch,
  timezone(m.tz, datecreated) as datecreatedlocal,
  timezone(m.tz, lastlogin) as lastloginlocal,
--  timezone(m.tz, dateapproved) as dateapprovedlocal,
  timezone(m.tz, dateupdated) as dateupdatedlocal
  from engine.__member as m
;

grant select on engine.member to web, term, sysop, member;
