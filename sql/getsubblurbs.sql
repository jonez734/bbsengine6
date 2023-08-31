CREATE OR REPLACE FUNCTION socrates.getreplies(integer)
 RETURNS SETOF socrates.post
 LANGUAGE sql
AS $function$ 
        with recursive t as 
                (select * from socrates.post where parentid=$1 union all select socrates.post.* from socrates.post join t on socrates.post.parentid=t.id) 
        select * from t; 
$function$
;
