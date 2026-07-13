create table if not exists bank.__transaction (
    "id" bigserial primary key,
    "accountid" bigint not null constraint fk_transaction_account references bank.__account(id) on delete cascade,
    "amount" numeric(10,0) not null,
    "transactiontype" text not null,
    "description" text,
    "relatedaccountid" bigint,
    "relatedmoniker" citext,
    "membermoniker" citext,
    "dateposted" timestamptz default now()
);

create index idx_transaction_account on bank.__transaction(accountid);
create index idx_transaction_date on bank.__transaction(dateposted);

grant select on bank.__transaction to web;
grant all on bank.__transaction to term, sysop;
grant all on bank.__transaction_id_seq to term, sysop;
