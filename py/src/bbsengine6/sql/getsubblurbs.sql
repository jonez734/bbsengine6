--\echo getsubblurbs.sql (legacy, see LEGACY.md)
-- Legacy recursive CTE that returns a blurb and all of its descendants.
-- Used by the bbsengine5 browse UI to walk blurb trees. Not part of
-- the new channel/pub-sub system (see channel.sql, net/transport.py).
-- Kept for backward compatibility.

CREATE OR REPLACE FUNCTION engine.getsubblurbs(bigint)
 RETURNS SETOF engine.__blurb
 LANGUAGE sql
AS $function$ 
        with recursive t as 
                (select * from engine.__blurb where parentid=$1 union all select engine.__blurb.* from engine.__blurb join t on engine.__blurb.parentid=t.id) 
        select * from t; 
$function$
;
