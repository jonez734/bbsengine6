\echo flagdata.sql
insert into engine.flag(name, defaultvalue, description) values ('SYSOP',  'f', 'SysOp Access');
insert into engine.flag(name, defaultvalue, description) values ('MAGIC',  'f', 'Magic Related');
insert into engine.flag(name, defaultvalue, description) values ('EROS',   'f', 'Adult Content');
insert into engine.flag(name, defaultvalue, description) values ('AUTHENTICATED', 'f', 'Authenticated Member');
insert into engine.flag(name, defaultvalue, description) values ('ASIMOV', 'f', 'project asimov');
insert into engine.flag(name, defaultvalue, description) values ('NOCALUMNI', 'f', 'NOC Alumni');
insert into engine.flag(name, defaultvalue, description) values ('EMAILVERIFIED', 'f', 'E-Mail Verified');
insert into engine.flag(name, defaultvalue, description) values ('APPROVED', 'f', 'Account Approved');

--insert into engine.flag(name, defaultvalue, description) values ('DRAFT',  'f', 'Draft');
--insert into engine.flag(name, defaultvalue, description) values ('FROZEN', 'f', 'Frozen');
--insert into engine.flag(name, defaultvalue, description) values ('JUNK',   'f', 'Junk');
