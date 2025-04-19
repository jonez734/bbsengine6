\echo view engine.blurb
create or replace view engine.blurb as
    select
        b.*,
--        array_to_json(array(select sigpath from engine.map_node_sig where engine.map_node_sig.nodeid = engine.__node.id order by sigpath)) as sigs,
        extract(epoch from b.datecreated) as datecreatedepoch,
        extract(epoch from b.dateupdated) as dateupdatedepoch,
        extract(epoch from b.dateapproved) as dateapprovedepoch,
--        coalesce(createdby.moniker,  'a. nonymous'::text) as createdbymoniker,
--        coalesce(updatedby.moniker,  'a. nonymous'::text) as updatedbymoniker,
--        coalesce(approvedby.moniker, 'a. nonymous'::text) as approvedbymoniker,
        array(select distinct map.sigpath from engine.map_blurb_sig as map where map.blurbid = b.id order by map.sigpath) AS sigs,
        array(select distinct map.tag from engine.map_blurb_tag as map where map.blurbid = b.id order by map.tag) as tags,
        (select count(id) from (select id from engine.__blurb as subblurb where subblurb.parentid=b.id) as subblurbs) as subblurbcount
    from engine.__blurb as b
    left join engine.__member as createdby ON (createdby.moniker = b.createdbymoniker)
    left join engine.__member as updatedby ON (updatedby.moniker = b.updatedbymoniker)
    left join engine.__member as approvedby ON (approvedby.moniker = b.approvedbymoniker)
;

\echo grant engine.blurb
grant select on engine.blurb to web;
