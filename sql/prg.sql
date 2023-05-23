--
-- prg modules are for things like 'socrates', 'empyre', 'ogun', etc
--

create or replace view engine.prg as
    select b.*,
        "lang" text,
        "module" text
    from engine.blurb as b
    where b.prg = 'engine.prg'
;

