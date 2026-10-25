-- Drop the engine views that are created with plain CREATE VIEW (not OR REPLACE).
--
-- checkclasses and the view files cannot replace these in place: CREATE VIEW fails on an
-- existing object. Run this once as a sysop, then restart the startup check so the views
-- are recreated from their files. Views created with CREATE OR REPLACE need no drop.
--
-- None of these views is read by another view in this repo, so they drop in any order.
-- IF EXISTS makes the file safe to re-run.

drop view if exists engine.folder;
drop view if exists engine.session;
