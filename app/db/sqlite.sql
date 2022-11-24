select * from t_gpt3_log limit 10;
-- where input is not null and input != '';


create table t_resource (
	uuid  TEXT NOT NULL,
	ts    text,
	topic text,
	url text,
	comment text
);
create unique index idx_resource on t_resource(uuid);
select ts,topic,url,comment,uuid from T_RESOURCE order by ts desc;
insert into t_resource (uuid, ts, topic, url, comment) 
values 
('400f2586-2d36-4bc7-b762-b73971d8a267', '2022-10-17 16:15:15.734865', 'openai-gpt3', 'https://beta.openai.com/docs/guides/code/introduction', ''),
('4c2d84b5-8594-4d15-a3ea-8259e03436de', '2022-10-19 21:04:04.485476', 'python', 'https://sparkbyexamples.com/pyspark-tutorial/', 'good resource for pyspark')
;


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
alter table t_gpt3_log drop column input;

create unique index idx_gpt3_log on t_gpt3_log(uuid);




SELECT 
    name
FROM 
    sqlite_schema
WHERE 
    type ='table' AND 
    name NOT LIKE 'sqlite_%';