--\echo alert
create table engine.__alert (
  "id" bigserial unique not null primary key,
  "membermoniker" citext not null constraint fk_alert_membermoniker references engine.__member(moniker) on update cascade on delete cascade,
  "sessionid" text constraint fk_alert_sessionid references engine.__session(id) on update cascade on delete set null,
  "type" text not null,
  "status" text not null,
  "displayed" boolean default 'f',
  "template" text not null,
  "urgent" boolean default 'f',
  "datecreated" timestamptz,
  "createdbymoniker" citext constraint fk_alert_createdbyid references engine.__member(moniker) on update cascade on delete set null,
  "dateupdated" timestamptz,
  "updatedbymoniker" citext constraint fk_alert_updatedbyid references engine.__member(moniker) on update cascade on delete set null,
  "datedisplayed" timestamptz,
  "data" jsonb
);

CREATE INDEX idx_engine_alert ON engine.__alert USING gin (data);

grant all on engine.__alert to web, term;
grant all on engine.__alert_id_seq to web;

create or replace view engine.alert as
  select a.*,
    extract(epoch from a.datecreated) as datecreatedepoch,
    extract(epoch from a.datedisplayed) as datedisplayedepoch,
    extract(epoch from a.dateupdated) as dateupdatedepoch,
    timezone(currentmember.tz, a.datedisplayed) as datedisplayedlocal,
    timezone(currentmember.tz, a.datecreated) as datecreatedlocal
  from engine.__alert as a
  left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;

--create or replace view engine.notify as
--  select n.*,
--  (attributes->>'memberid')::bigint as memberid constraint fk_notify_memberid references engine.__member(id) on update cascade on delete set cascade,
--  (attributes->>'sessionid')::text as sessionid,
--  (attributes->>'urgent')::boolean as urgent,
--  (attributes->>'status')::boolean as status,
--  (attributes->>'type')::text as type,
--  (attributes->>'template')::text as template,
--  (attributes->>'data')::jsonb as data
--  from engine.__notify as n
--;

grant select on engine.alert to web;
grant all on engine.alert to sysop;
--create or replace language plpython3u;

-- copied from trailersdemo, originally written 2016-mar-31 with help from #postgresql
-- this trigger deletes a notify if the memberid and the sessionid are both None
---CREATE or replace FUNCTION checkalert()
---  RETURNS trigger
---AS $$
---    plpy.log("checkalert.100: inside checkalert()")
---    if TD["when"] == "BEFORE" and TD["level"] == "ROW" and TD["event"] == "UPDATE" and TD["old"]["membermoniker"] is None and TD["old"]["sessionid"] is None:
---      plpy.execute("delete from alert where membermoniker is null and sessionid is null")
---      plpy.log("checkalert.110: executed delete")
---      return "SKIP"
---    plpy.log("checkalert.115: did not execute delete")
---    return "OK"
---$$ LANGUAGE plpython3u;
CREATE OR REPLACE function engine.checkalert_func()
returns trigger 
language plpgsql 
as $$
  BEGIN
  IF OLD.membermoniker IS NULL AND OLD.sessionid IS NULL THEN
    DELETE FROM engine.__alert WHERE membermoniker IS NULL AND sessionid IS NULL;
  END IF;
  return new;
END;
$$;

grant execute on function engine.checkalert_func to term, web;

create trigger checkalert before update of membermoniker, sessionid on engine.__alert for each row execute procedure engine.checkalert_func();

-- grant select, insert, update on engine.__notify to apache;
grant select on engine.alert to web;

--alter table engine.__alert drop column displayed;
--alter table engine.__alert alter column data type jsonb using data::jsonb;
--alter table engine.__alert drop column datedisplayed;
--alter table engine.__alert add column template text not null;
--alter table engine.__alert add column urgent boolean default 'f';
--alter table engine.__alert alter column sessionid drop not null ;
