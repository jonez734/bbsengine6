--
-- prg modules are for things like 'socrates', 'empyre', 'ogun', etc
--

create or replace view engine.prg as
    select n.*,
        "language" text,
        "module" text
    from engine.node
    where attributes ? 'language' and attributes ? 'module'
;
