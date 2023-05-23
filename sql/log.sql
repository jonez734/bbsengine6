create or replace view engine.log as
    select
        b.*
    from engine.blurb as b
    where prg='engine.log'
;
