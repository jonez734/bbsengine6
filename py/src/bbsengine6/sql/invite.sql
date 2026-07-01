--\echo invite.sql
--
-- Generic Invite Code System
--
-- A shared invite code table that any module (casino, empyre, murdermotel,
-- member, etc.) can use to gate access to its resources (tables, islands,
-- rooms, etc.) via short alphanumeric codes.
--
-- Usage:
--   create_invite(module='casino', resourceid='blackjack-1', code='aB3xK9pQ', ...)
--   validate_invite(module='casino', resourceid='blackjack-1', code='aB3xK9pQ')
--   mark_used(invite_id=42, usedbymoniker='alice')
--   revoke_invite(invite_id=42)

create table if not exists engine.__invite (
    "id" bigserial unique not null primary key,
    "module" text not null,
    "resourceid" text not null,
    "code" text not null,
    "createdbymoniker" citext constraint fk_invite_createdby
        references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz not null default now(),
    "dateexpires" timestamptz,
    "dateused" timestamptz,
    "usedbymoniker" citext constraint fk_invite_usedby
        references engine.__member(moniker) on update cascade on delete set null,
    "revoked" timestamptz,
    -- Module-specific FK for referential integrity.
    -- Populated only when module='casino'; deleting a casino table cascades
    -- to its invites. Additional module FKs can be added in the same shape.
    "casinotablemoniker" citext constraint fk_invite_casinotable
        references casino.__table(moniker) on update cascade on delete cascade,
    constraint chk_invite_not_used_and_revoked
        check (not (dateused is not null and revoked is not null))
);

create index if not exists idx_invite_module_resource
    on engine.__invite(module, resourceid);
create index if not exists idx_invite_code
    on engine.__invite(module, code);
create index if not exists idx_invite_createdby
    on engine.__invite(createdbymoniker);
create index if not exists idx_invite_casinotable
    on engine.__invite(casinotablemoniker);

-- Prevent duplicate active codes per resource. Allows re-issuing a code
-- once the previous one has been used or revoked.
create unique index if not exists idx_invite_active_code
    on engine.__invite(module, resourceid, code)
    where revoked is null and dateused is null;

-- View with local-timezone conversion (mirrors engine.session view pattern).
-- The joined engine.__member row is determined by CURRENT_USER's loginid,
-- so each caller sees timestamps in their own configured timezone.
create or replace view engine.invite as
    select
        i.id,
        i.module,
        i.resourceid,
        i.code,
        i.createdbymoniker,
        i.datecreated,
        i.dateexpires,
        i.dateused,
        i.usedbymoniker,
        i.revoked,
        i.casinotablemoniker,
        extract(epoch from i.datecreated) as datecreatedepoch,
        extract(epoch from i.dateexpires) as dateexpiresepoch,
        extract(epoch from i.dateused) as dateusedepoch,
        extract(epoch from i.revoked) as revokedepoch,
        timezone(currentmember.tz, i.datecreated) as datecreatedlocal,
        timezone(currentmember.tz, i.dateexpires) as dateexpireslocal,
        timezone(currentmember.tz, i.dateused) as dateusedlocal,
        timezone(currentmember.tz, i.revoked) as revokedlocal
    from engine.__invite as i
    left outer join engine.__member as currentmember
        on (currentmember.loginid = current_user);

-- Grants
grant select, insert, update, delete on engine.__invite to web, term, sysop;
-- member is intentionally NOT granted write on __invite; see pgrole.sql
-- and handbook/specs/pg-ident-auth.md.
grant all on engine.__invite_id_seq to web, term, sysop;
grant select on engine.invite to web, term, sysop, member;
