\echo memberview.sql
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
  (select count(notify1.id) from engine.notify as notify1 where notify1.memberid = m.id) as notifycount,
  (select count(notify2.id) from engine.notify as notify2 where notify2.memberid = m.id and notify2.status='sent') as sentnotifycount,
--  loginid,
--  shell,
--  (attributes->>'loginid')::text as loginid,
  extract(epoch from m.datecreated) as datecreatedepoch,
  extract(epoch from m.lastlogin) as lastloginepoch,
  extract(epoch from m.dateapproved) as dateapprovedepoch,
  extract(epoch from m.dateupdated) as dateupdatedepoch
  from engine.__member as m
;

grant select on engine.member to :web;
