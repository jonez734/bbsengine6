create or replace view engine.blurb as
    select
        b.*,
--        array_to_json(array(select sigpath from engine.map_node_sig where engine.map_node_sig.nodeid = engine.__node.id order by sigpath)) as sigs,
        extract(epoch from b.datecreated) as datecreatedepoch,
        extract(epoch from b.dateupdated) as dateupdatedepoch,
        extract(epoch from b.dateapproved) as dateapprovedepoch,
        coalesce(m1.name, 'a. nonymous'::text) as createdbyname,
        coalesce(m2.name, 'a. nonymous'::text) as updatedbyname,
        coalesce(m3.name, 'a. nonymous'::text) as approvedbyname,
        array(select distinct map.sigpath from engine.map_blurb_sig as map where map.blurbid = b.id order by map.sigpath) AS sigs,
        array(select distinct map.tag from engine.map_blurb_tag as map where map.blurbid = b.id order by map.tag) as tags,
        (select count(id) from (select id from engine.__blurb as subblurb where subblurb.parentid=b.id) as subblurbs) as subblurbcount
    from engine.__blurb as b
    left join engine.__member as m1 ON (m1.id = b.createdbyid)
    left join engine.__member as m2 ON (m2.id = b.updatedbyid)
    left join engine.__member as m3 ON (m3.id = b.approvedbyid)
;

\echo grant engine.blurb
grant select on engine.blurb to :web;
