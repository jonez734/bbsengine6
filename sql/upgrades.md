- 20240926 
  * added 'refcode' table and view
  * drop view engine.member;
  * alter table engine.__member add column refcode text constraint fk_engine_member_refcode references engine.__refcode(code);
- 