-- engine.log_action: the single writer for engine.__actionlog.
--
-- Every login, login failure, logout, token expiry and client exit is recorded through this function.
-- A client_exit carries its reason in the note: quit, eof, intr, idle, ws_error, auth_failed or error. It is
-- SECURITY DEFINER and owned by zoid6, which is the only role that inserts into the log, so no
-- caller gets a direct insert. The search_path is pinned so a caller cannot redirect it.
--
-- The action must be one of the known values; anything else is rejected, so a typo cannot
-- create a new kind of row silently.
--
-- Installed by checkfunctions as the owner. Idempotent.

create or replace function engine.log_action(
    p_moniker citext,
    p_action text,
    p_remoteaddr inet,
    p_note text default null
)
returns void
language plpgsql
security definer
set search_path = engine, public, pg_temp
as $$
begin
    if p_action not in ('login', 'login_failed', 'logout', 'auth_expired', 'client_exit') then
        raise exception 'log_action: unknown action %', p_action;
    end if;

    -- A client_exit records why the client ended. The reason is the note, and it must be one
    -- of a fixed vocabulary, so the log stays queryable and free text cannot slip in.
    if p_action = 'client_exit' then
        if p_note is null then
            raise exception 'log_action: client_exit requires a reason';
        end if;
        if p_note not in ('quit', 'eof', 'intr', 'idle', 'ws_error', 'auth_failed', 'error') then
            raise exception 'log_action: unknown reason %', p_note;
        end if;
    end if;

    insert into engine.__actionlog (moniker, action, actiondate, remoteaddr, note)
    values (p_moniker, p_action, now(), p_remoteaddr, p_note);
end
$$;

alter function engine.log_action(citext, text, inet, text) owner to zoid6;
revoke all on function engine.log_action(citext, text, inet, text) from public;
grant execute on function engine.log_action(citext, text, inet, text) to bed, web, term;
