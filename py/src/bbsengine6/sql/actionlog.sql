-- engine.__actionlog: the append-only action and login log.
--
-- Rows are written only by the zoid6-owned writer function (engine.log_action, phase 2), so no
-- role gets a direct insert. No role gets update or delete: the log is never edited. The view
-- is in actionlog_view.sql.
create table if not exists engine.__actionlog (
    moniker text constraint fk_actionlog_moniker references engine.__member(moniker) on update cascade on delete cascade,
    action text not null,
    actiondate timestamptz,
    remoteaddr inet,
    note text
);

-- Read-only access for review. Insert is granted to the writer function's owner only.
grant select on engine.__actionlog to sysop, member;
