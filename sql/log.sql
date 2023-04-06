create or replace view engine.log as
    select
        n.*
    from engine.node as n
    where prg='engine.log'
;
