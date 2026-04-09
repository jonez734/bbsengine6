--\echo flagdata.sql
insert into engine.member_flag(name, defaultvalue, description) values ('SYSOP',  'f', 'SysOp Access');
insert into engine.member_flag(name, defaultvalue, description) values ('MAGIC',  'f', 'Magician');
insert into engine.member_flag(name, defaultvalue, description) values ('EROS',   'f', 'Adult Content');
insert into engine.member_flag(name, defaultvalue, description) values ('AUTHENTICATED', 'f', 'Authenticated Member');
insert into engine.member_flag(name, defaultvalue, description) values ('ASIMOV', 'f', 'Project Asimov');
insert into engine.member_flag(name, defaultvalue, description) values ('NOCALUMNI', 'f', 'NOC Alumni');
insert into engine.member_flag(name, defaultvalue, description) values ('EMAILVERIFIED', 'f', 'E-Mail Verified');
insert into engine.member_flag(name, defaultvalue, description) values ('APPROVED', 'f', 'Account Approved');

--insert into engine.member_flag(name, defaultvalue, description) values ('DRAFT',  'f', 'Draft');
--insert into engine.member_flag(name, defaultvalue, description) values ('FROZEN', 'f', 'Frozen');
--insert into engine.member_flag(name, defaultvalue, description) values ('JUNK',   'f', 'Junk');
