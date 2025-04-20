\echo blocklist.sql
create table engine.__blocklist (
    id bigserial unique not null primary key
    address cidr unique not null, -- /32 for one address, or /27 for a bigger block, also works w ipv6
    notes text,
    status text,
    datecreated timestamptz,
    createdbymoniker bigint constraint fk_blocklist_createdbymoniker references engine.__member(moniker) on update cascade on delete set null,
    dateupdated timestamptz,
    updatedbymoniker citext constraint fk_blocklist_updatedbymoniker references engine.__member(moniker) on update cascade on delete set null
);

-- insert into __blocklist (1, "192.168.1.0/24");
-- insert into __blocklist (2, "192.168.1.100/32");
