create table __blocklist (
    id bigserial unique not null primary key
    address cidr not null, -- /32 for one address, or /27 for a bigger block, also works w ipv6
    notes text,
    status text,
    datecreated timestamptz,
    createdbyid bigint,
    dateupdated timestamptz,
    updatedbyid bigint
);

-- insert into __blocklist (1, "192.168.1.0/24");
-- insert into __blocklist (2, "192.168.1.100/32");
