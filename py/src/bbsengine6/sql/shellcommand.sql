create or replace table engine.shellcommand (
    "id" bigint unique not null primary key,
    "name" text unique not null,
    "title" text not null,
    "help" text,
    "path" text
);

