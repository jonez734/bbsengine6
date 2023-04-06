CREATE OR REPLACE FUNCTION engine.getsubnodes(bigint)
 RETURNS SETOF engine.__node
 LANGUAGE sql
AS $function$ 
        with recursive t as 
                (select * from engine.__node where parentid=$1 union all select engine.__node.* from engine.__node join t on engine.__node.parentid=t.id) 
        select * from t; 
$function$
;
