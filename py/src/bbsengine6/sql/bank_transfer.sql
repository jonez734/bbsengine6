create table if not exists bank.__transfer (
    "id" bigserial primary key,
    "fromaccountid" bigint not null constraint fk_transfer_from references bank.__account(id) on delete cascade,
    "toaccountid" bigint not null constraint fk_transfer_to references bank.__account(id) on delete cascade,
    "amount" numeric(10,0) not null,
    "status" text default 'pending',
    "requestedby" citext,
    "requestedat" timestamptz default now(),
    "respondedby" citext,
    "respondedat" timestamptz
);

create index idx_transfer_status on bank.__transfer(status);
create index idx_transfer_accounts on bank.__transfer(fromaccountid, toaccountid);

grant select on bank.__transfer to web;
grant all on bank.__transfer to term, sysop;
grant all on bank.__transfer_id_seq to term, sysop;
