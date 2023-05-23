CREATE OR REPLACE FUNCTION engine.getsubblurbs(bigint)
 RETURNS SETOF engine.__blurb
 LANGUAGE sql
AS $function$ 
        with recursive t as 
                (select * from engine.__blurb where parentid=$1 union all select engine.__blurb.* from engine.__blurb join t on engine.__blurb.parentid=t.id) 
        select * from t; 
$function$
;
