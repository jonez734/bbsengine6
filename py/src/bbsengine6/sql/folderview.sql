create view engine.folder as
 select 
  s.*
--  coalesce(m1.moniker, 'a. nonymous'::text) as createdbymoniker,
--  coalesce(m2.moniker, 'a. nonymous'::text) as updatedbymoniker,
--  coalesce(m3.moniker, 'a. nonymous'::text) as approvedbymoniker
 from engine.__folder as s
 left join engine.__member as m1 ON (m1.moniker = s.createdbymoniker)
 left join engine.__member as m2 ON (m2.moniker = s.updatedbymoniker)
 left join engine.__member as m3 ON (m2.moniker = s.approvedbymoniker)
;

--create unique index idx_engine_sig_path on engine.__sig(path);

grant select on engine.folder to web, term, sysop, member;
