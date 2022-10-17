select * from t_gpt3_log;

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

SELECT 
    name
FROM 
    sqlite_schema
WHERE 
    type ='table' AND 
    name NOT LIKE 'sqlite_%';