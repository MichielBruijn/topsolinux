set nocount on;
select name, physical_name from sys.master_files where database_id in (2,3,4);
alter database model modify file (name = modeldev, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\model.mdf');
alter database model modify file (name = modellog, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\modellog.ldf');
alter database msdb modify file (name = MSDBData, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\msdbdata.mdf');
alter database msdb modify file (name = MSDBLog, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\msdblog.ldf');
alter database tempdb modify file (name = tempdev, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\tempdb.mdf');
alter database tempdb modify file (name = templog, filename = 'C:\Program Files\Microsoft SQL Server\MSSQL15.SQLTOPSOLID\MSSQL\DATA\templog.ldf');
go
