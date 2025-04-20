\echo group
create table engine.__group (
    "name" text unique not null primary key,
    "title" text unique not null,
    "attributes" jsonb
);
