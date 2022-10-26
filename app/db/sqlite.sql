select * from t_gpt3_log;

update t_gpt3_log set use_case='SQL';

create table t_gpt3_log (
	uuid  TEXT NOT NULL,
	ts    text,
	use_case text,
	settings text,
	prompt text,
	input text,
	output text,
	comment text
);

alter table t_gpt3_log add column valid_output text;

create unique index idx_gpt3_log on t_gpt3_log(uuid);

SELECT 
    name
FROM 
    sqlite_schema
WHERE 
    type ='table' AND 
    name NOT LIKE 'sqlite_%';