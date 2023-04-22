create or replace view engine.blurb as
    select
        n.*,
--        array_to_json(array(select sigpath from engine.map_node_sig where engine.map_node_sig.nodeid = engine.__node.id order by sigpath)) as sigs,
        extract(epoch from n.datecreated) as datecreatedepoch,
        extract(epoch from n.dateupdated) as dateupdatedepoch,
        extract(epoch from n.dateapproved) as dateapprovedepoch,
        coalesce(m1.name, 'a. nonymous'::text) as createdbyname,
        coalesce(m2.name, 'a. nonymous'::text) as updatedbyname,
        coalesce(m3.name, 'a. nonymous'::text) as approvedbyname,
        array(select distinct map.sigpath from engine.map_blurb_sig as map where map.blurbid = n.id order by map.sigpath) AS sigs,
        array(select distinct map.tag from engine.map_blurb_tag as map where map.blurbid = n.id order by map.tag) as tags,
        (select count(id) from (select id from engine.__blurb as subblurb where subblurb.parentid=n.id) as subblurbs) as subblurbcount
    from engine.__blurb as n
    left join engine.__member as m1 ON (m1.id = n.createdbyid)
    left join engine.__member as m2 ON (m2.id = n.updatedbyid)
    left join engine.__member as m3 ON (m3.id = n.approvedbyid)
;

\echo grant engine.blurb
grant select on engine.blurb to apache;
