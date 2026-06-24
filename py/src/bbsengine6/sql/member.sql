--\echo member.sql

create table engine.__member (
--  "id" bigserial unique not null primary key,
  "moniker" citext unique not null constraint chk_member_moniker_format check (moniker ~ '^[a-zA-Z0-9_]+$'),
  "email" text not null,
  "password" text,
  "credits" numeric(10,0),
  "parentmoniker" citext constraint fk_member_parentid references engine.__member(moniker) on update cascade on delete set null,
  "datecreated" timestamptz,
  "createdbymoniker" citext constraint fk_member_createdbyid references engine.__member(moniker) on update cascade on delete set null,
  "dateupdated" timestamptz,
  "updatedbymoniker" citext constraint fk_member_updatedbyid references engine.__member(moniker) on update cascade on delete set null,
  "approvedbymoniker" citext constraint fk_member_approvedbyid references engine.__member(moniker) on update cascade on delete set null,
  "dateapproved" timestamptz,
--  "emailverified" boolean,
--  "emailverifiedbymoniker" text constraint fk_member_emailverifiedbyid references engine.__member(moniker) on update cascade on delete set null,
--  "dateemailverified" timestamptz,
--  "verifiedbymoniker" text constraint fk_member_verifiedbyid references engine.__member(moniker) on update cascade on delete set null,
--  "dateverified" timestamptz,
  "lastlogin" timestamptz,
  "lastloginfrom" inet,
  "loginid" text,
  "ui" citext,
  "tz" citext,
  "attrs" jsonb,
  "refcode" citext
);

grant select, update on engine.__member to web, term;
grant all on engine.__member to sysop;

--grant usage, select on engine.__member_id_seq to web, term;
--grant all on engine.__member_id_seq to sysop;
