-- bbsengine6/sql/migrate_member_terminaltype.sql
-- Migration: a stored terminal type per member. Idempotent.
--
-- terminaltype: the member's terminal type, used when the client's TERM has no terminfo entry
--   (see bbsengine6.io.terminal.resolve). The default is xterm; the console edit key only
--   accepts values that pass the terminfo check.

alter table engine.__member
    add column if not exists "terminaltype" text not null default 'xterm';

comment on column engine.__member.terminaltype is
  'Terminal type (terminfo name) used when the client TERM has no entry. Default xterm.';
