drop table if exists capture_item;

create table capture_item(
  group_name varchar(50) not null,
  source_name varchar(50) not null,
  source_path text,
  creation_time timestamp not null,
  update_time timestamp not null
)