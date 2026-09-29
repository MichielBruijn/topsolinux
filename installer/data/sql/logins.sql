set nocount on;
if not exists (select * from sys.server_principals where name = 'BUILTIN\Administrators')
    create login [BUILTIN\Administrators] from windows;
alter server role sysadmin add member [BUILTIN\Administrators];
alter login sa disable;
select name, type_desc, is_disabled from sys.server_principals where type in ('S','U','G') order by name;
go
