\echo member.sql

create table engine.__member (
  "id" bigserial unique not null primary key,
  "name" text unique not null,
  "email" text,
  "password" text,
  "credits" numeric(10,0),
  "parentid" bigint constraint fk_member_parentid references engine.__member(id) on update cascade on delete set null,
  "datecreated" timestamptz,
  "createdbyid" bigint constraint fk_member_createdbyid references engine.__member(id) on update cascade on delete set null,
  "dateupdated" timestamptz,
  "updatedbyid" bigint constraint fk_member_updatedbyid references engine.__member(id) on update cascade on delete set null,
  "approvedbyid" bigint constraint fk_member_approvedbyid references engine.__member(id) on update cascade on delete set null,
  "dateapproved" timestamptz,
  "lastlogin" timestamptz,
  "lastloginfrom" inet,
  "loginid" text,
  "shell" text,
  "ui" text,
  "attributes" jsonb
);

grant all on engine.__member to apache;
grant all on engine.__member_id_seq to apache;
