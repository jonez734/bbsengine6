create table "member" (
  "id" serial unique not null primary key,
  "emailaddress" text not null,
  "fullname" text,
  "password" text,
  "lastlogin" timestamptz,
  "lastloginfrom" inet,
  "dateregistered" timestamptz
);

grant all on "member" to "www-data";
grant all on "member_id_seq" to "www-data";

create table "__release" (
  "id" serial unique not null primary key,
  "name" text unique not null,
  "title" text unique not null,
  "datereleased" timestamptz,
  "releasedbyid" integer,
  "project" text,
  "releasenotes" text,
  "access" text
);

grant all on "__release" to "www-data";
grant all on "__release_id_seq" to "www-data";

create view "release" as 
  select __release.*,
    extract(epoch from __release.datereleased) as datereleasedepoch,
    releasedby.fullname as releasedbyname
  from __release
  left outer join member as releasedby on (releasedby.id = __release.releasedbyid);

grant all on "release" to "www-data";

create table "__file" (
  "id" serial unique not null primary key,
  "releaseid" integer,
  "filepath" text unique not null,
  "filesize" integer,
  "filetype" text,
  "totaldownloads" integer default 0,
  "datelastdownloaded" timestamptz,
  "dateuploaded" timestamptz,
  "uploadedbyid" integer,
  "lastdownloadedbyid" integer,
  "access" text
);

grant all on "__file" to "www-data";
grant all on "__file_id_seq" to "www-data";

alter table "__file"
  add constraint "fk_file_uploadedbyid" foreign key (uploadedbyid) references member(id) on update cascade on delete set null;
alter table "__file"
  add constraint "fk_file_releaseid" foreign key (releaseid) references __release(id) on update cascade on delete set null;
alter table "__file"
  add constraint "fk_file_lastdownloadedbyid" foreign key (lastdownloadedbyid) references member(id) on update cascade on delete set null;

create view "file" as 
  select __file.*,
    extract(epoch from __file.dateuploaded) as dateuploadedepoch,
    extract(epoch from __file.datelastdownloaded) as datelastdownloadedepoch,
    uploadedby.fullname as uploadedbyname,
    lastdownloadedby.fullname as lastdownloadedbyname
  from __file
  left outer join member as uploadedby on (uploadedby.id = __file.uploadedbyid) 
  left outer join member as lastdownloadedby on (lastdownloadedby.id = __file.lastdownloadedbyid);

grant all on "file" to "www-data";

create table "flag" (
  "name" text unique,
  "defaultvalue" boolean,
  "description" text
);

insert into "flag"("name", "defaultvalue", "description") values ('ADMIN', 'f', 'Administrator Access');

grant all on "flag" to "www-data";

create table "map_member_flag" (
  "flagname" text,
  "memberid" integer,
  "value" boolean
);

grant all on "map_member_flag" to "www-data";
