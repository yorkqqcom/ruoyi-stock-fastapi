-- ----------------------------
-- Tushare妯″潡锛圥ostgreSQL锛夛細琛ㄧ粨鏋?+ 鑿滃崟 + 杩愯琛?-- 鏂扮幆澧冩墽琛屾湰鏂囦欢鍗冲彲锛涙棫搴撳崌绾ц migrations_pg.sql
-- ----------------------------
-- ========== 1. 琛ㄧ粨鏋?==========
-- ----------------------------
-- 1銆乀ushare鎺ュ彛閰嶇疆琛?
-- ----------------------------
drop table if exists tushare_api_config;
create table tushare_api_config (
  config_id           bigserial      not null,
  api_name            varchar(100)   not null,
  api_code            varchar(100)   not null,
  api_desc            text,
  api_params          text,
  data_fields         text,
  primary_key_fields  text,
  status              char(1)        default '0',
  create_by           varchar(64)     default '',
  create_time         timestamp(0),
  update_by           varchar(64)     default '',
  update_time         timestamp(0),
  remark              varchar(500)   default '',
  primary key (config_id),
  constraint uk_api_code unique (api_code)
);
comment on column tushare_api_config.config_id is '閰嶇疆ID';
comment on column tushare_api_config.api_name is '鎺ュ彛鍚嶇О';
comment on column tushare_api_config.api_code is '鎺ュ彛浠ｇ爜锛堝锛歴tock_basic锛?;
comment on column tushare_api_config.api_desc is '鎺ュ彛鎻忚堪';
comment on column tushare_api_config.api_params is '鎺ュ彛鍙傛暟锛圝SON鏍煎紡锛?;
comment on column tushare_api_config.data_fields is '鏁版嵁瀛楁锛圝SON鏍煎紡锛岀敤浜庢寚瀹氶渶瑕佷笅杞界殑瀛楁锛?;
comment on column tushare_api_config.primary_key_fields is '涓婚敭瀛楁閰嶇疆锛圝SON鏍煎紡锛屼负绌哄垯浣跨敤榛樿data_id涓婚敭锛?;
comment on column tushare_api_config.status is '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?;
comment on column tushare_api_config.create_by is '鍒涘缓鑰?;
comment on column tushare_api_config.create_time is '鍒涘缓鏃堕棿';
comment on column tushare_api_config.update_by is '鏇存柊鑰?;
comment on column tushare_api_config.update_time is '鏇存柊鏃堕棿';
comment on column tushare_api_config.remark is '澶囨敞淇℃伅';
comment on table tushare_api_config is 'Tushare鎺ュ彛閰嶇疆琛?;

-- ----------------------------
-- 2銆乀ushare涓嬭浇浠诲姟琛?
-- ----------------------------
drop table if exists tushare_download_task;
create table tushare_download_task (
  task_id             bigserial      not null,
  task_name           varchar(100)   not null,
  config_id           bigint,
  workflow_id         bigint,
  task_type           varchar(20)    default 'single',
  cron_expression     varchar(255),
  start_date          varchar(20),
  end_date            varchar(20),
  task_params         text,
  save_path           varchar(500),
  save_format         varchar(20)    default 'csv',
  save_to_db          char(1)        default '0',
  data_table_name     varchar(100),
  status              char(1)        default '0',
  last_run_time       timestamp(0),
  next_run_time       timestamp(0),
  run_count           integer        default 0,
  success_count       integer        default 0,
  fail_count          integer        default 0,
  create_by           varchar(64)    default '',
  create_time         timestamp(0),
  update_by           varchar(64)    default '',
  update_time         timestamp(0),
  remark              varchar(500)   default '',
  primary key (task_id),
  constraint uk_task_name unique (task_name)
);
create index idx_config_id on tushare_download_task(config_id);
create index idx_workflow_id_task on tushare_download_task(workflow_id);
create index idx_task_type on tushare_download_task(task_type);
comment on column tushare_download_task.task_id is '浠诲姟ID';
comment on column tushare_download_task.task_name is '浠诲姟鍚嶇О';
comment on column tushare_download_task.config_id is '鎺ュ彛閰嶇疆ID锛堟祦绋嬮厤缃ā寮忎笅鍙互涓虹┖锛?;
comment on column tushare_download_task.workflow_id is '娴佺▼閰嶇疆ID锛堝鏋滃瓨鍦ㄥ垯鎵ц娴佺▼锛屽惁鍒欐墽琛屽崟涓帴鍙ｏ級';
comment on column tushare_download_task.task_type is '浠诲姟绫诲瀷锛坰ingle:鍗曚釜鎺ュ彛 workflow:娴佺▼閰嶇疆锛?;
comment on column tushare_download_task.cron_expression is 'cron鎵ц琛ㄨ揪寮?;
comment on column tushare_download_task.start_date is '寮€濮嬫棩鏈燂紙YYYYMMDD锛?;
comment on column tushare_download_task.end_date is '缁撴潫鏃ユ湡锛圷YYYMMDD锛?;
comment on column tushare_download_task.task_params is '浠诲姟鍙傛暟锛圝SON鏍煎紡锛岃鐩栨帴鍙ｉ粯璁ゅ弬鏁帮級';
comment on column tushare_download_task.save_path is '淇濆瓨璺緞';
comment on column tushare_download_task.save_format is '淇濆瓨鏍煎紡锛坈sv/excel/json锛?;
comment on column tushare_download_task.save_to_db is '鏄惁淇濆瓨鍒版暟鎹簱锛?鍚?1鏄級';
comment on column tushare_download_task.data_table_name is '鏁版嵁瀛樺偍琛ㄥ悕锛堜负绌哄垯浣跨敤榛樿琛╰ushare_data锛?;
comment on column tushare_download_task.status is '鐘舵€侊紙0姝ｅ父 1鏆傚仠锛?;
comment on column tushare_download_task.last_run_time is '鏈€鍚庤繍琛屾椂闂?;
comment on column tushare_download_task.next_run_time is '涓嬫杩愯鏃堕棿';
comment on column tushare_download_task.run_count is '杩愯娆℃暟';
comment on column tushare_download_task.success_count is '鎴愬姛娆℃暟';
comment on column tushare_download_task.fail_count is '澶辫触娆℃暟';
comment on column tushare_download_task.create_by is '鍒涘缓鑰?;
comment on column tushare_download_task.create_time is '鍒涘缓鏃堕棿';
comment on column tushare_download_task.update_by is '鏇存柊鑰?;
comment on column tushare_download_task.update_time is '鏇存柊鏃堕棿';
comment on column tushare_download_task.remark is '澶囨敞淇℃伅';
comment on table tushare_download_task is 'Tushare涓嬭浇浠诲姟琛?;

-- ----------------------------
-- 3銆乀ushare涓嬭浇鏃ュ織琛?
-- ----------------------------
drop table if exists tushare_download_log;
create table tushare_download_log (
  log_id              bigserial      not null,
  task_id             bigint         not null,
  task_name           varchar(100)   not null,
  config_id           bigint         not null,
  api_name            varchar(100)   not null,
  download_date       varchar(20),
  record_count        integer        default 0,
  file_path           varchar(500),
  status              char(1)        default '0',
  error_message       text,
  duration            integer,
  create_time         timestamp(0),
  primary key (log_id)
);
create index idx_task_id on tushare_download_log(task_id);
create index idx_config_id on tushare_download_log(config_id);
create index idx_create_time on tushare_download_log(create_time);
comment on column tushare_download_log.log_id is '鏃ュ織ID';
comment on column tushare_download_log.task_id is '浠诲姟ID';
comment on column tushare_download_log.task_name is '浠诲姟鍚嶇О';
comment on column tushare_download_log.config_id is '鎺ュ彛閰嶇疆ID';
comment on column tushare_download_log.api_name is '鎺ュ彛鍚嶇О';
comment on column tushare_download_log.download_date is '涓嬭浇鏃ユ湡锛圷YYYMMDD锛?;
comment on column tushare_download_log.record_count is '璁板綍鏁?;
comment on column tushare_download_log.file_path is '鏂囦欢璺緞';
comment on column tushare_download_log.status is '鎵ц鐘舵€侊紙0鎴愬姛 1澶辫触锛?;
comment on column tushare_download_log.error_message is '閿欒淇℃伅';
comment on column tushare_download_log.duration is '鎵ц鏃堕暱锛堢锛?;
comment on column tushare_download_log.create_time is '鍒涘缓鏃堕棿';
comment on table tushare_download_log is 'Tushare涓嬭浇鏃ュ織琛?;

-- ----------------------------
-- 4銆乀ushare鏁版嵁瀛樺偍琛紙閫氱敤琛紝浣跨敤JSONB瀛樺偍鐏垫椿鏁版嵁锛?
-- ----------------------------
drop table if exists tushare_data;
create table tushare_data (
  data_id             bigserial      not null,
  task_id             bigint         not null,
  config_id           bigint         not null,
  api_code           varchar(100)    not null,
  download_date       varchar(20),
  data_content        jsonb,
  create_time         timestamp(0)   default current_timestamp,
  primary key (data_id)
);
create index idx_task_id_data on tushare_data(task_id);
create index idx_config_id_data on tushare_data(config_id);
create index idx_api_code_data on tushare_data(api_code);
create index idx_download_date_data on tushare_data(download_date);
create index idx_create_time_data on tushare_data(create_time);
-- 涓篔SONB瀛楁鍒涘缓GIN绱㈠紩浠ユ敮鎸侀珮鏁堟煡璇?
create index idx_data_content_gin on tushare_data using gin(data_content);
comment on column tushare_data.data_id is '鏁版嵁ID';
comment on column tushare_data.task_id is '浠诲姟ID';
comment on column tushare_data.config_id is '鎺ュ彛閰嶇疆ID';
comment on column tushare_data.api_code is '鎺ュ彛浠ｇ爜';
comment on column tushare_data.download_date is '涓嬭浇鏃ユ湡锛圷YYYMMDD锛?;
comment on column tushare_data.data_content is '鏁版嵁鍐呭锛圝SONB鏍煎紡锛?;
comment on column tushare_data.create_time is '鍒涘缓鏃堕棿';
comment on table tushare_data is 'Tushare鏁版嵁瀛樺偍琛紙閫氱敤琛級';

-- ----------------------------
-- 5銆乀ushare娴佺▼閰嶇疆琛?
-- ----------------------------
drop table if exists tushare_workflow_config;
create table tushare_workflow_config (
  workflow_id          bigserial      not null,
  workflow_name        varchar(100)   not null,
  workflow_desc        text,
  status               char(1)        default '0',
  create_by            varchar(64)    default '',
  create_time          timestamp(0),
  update_by            varchar(64)    default '',
  update_time          timestamp(0),
  remark               varchar(500)   default '',
  primary key (workflow_id),
  constraint uk_workflow_name unique (workflow_name)
);
comment on column tushare_workflow_config.workflow_id is '娴佺▼ID';
comment on column tushare_workflow_config.workflow_name is '娴佺▼鍚嶇О';
comment on column tushare_workflow_config.workflow_desc is '娴佺▼鎻忚堪';
comment on column tushare_workflow_config.status is '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?;
comment on column tushare_workflow_config.create_by is '鍒涘缓鑰?;
comment on column tushare_workflow_config.create_time is '鍒涘缓鏃堕棿';
comment on column tushare_workflow_config.update_by is '鏇存柊鑰?;
comment on column tushare_workflow_config.update_time is '鏇存柊鏃堕棿';
comment on column tushare_workflow_config.remark is '澶囨敞淇℃伅';
comment on table tushare_workflow_config is 'Tushare娴佺▼閰嶇疆琛?;

-- ----------------------------
-- 6銆乀ushare娴佺▼姝ラ琛?
-- ----------------------------
drop table if exists tushare_workflow_step;
create table tushare_workflow_step (
  step_id              bigserial      not null,
  workflow_id          bigint         not null,
  step_order           integer        not null,
  step_name            varchar(100)   not null,
  config_id            bigint         not null,
  step_params          text,
  condition_expr       text,
  position_x           integer,
  position_y           integer,
  node_type            varchar(20)    default 'task',
  source_step_ids      text,
  target_step_ids      text,
  layout_data          jsonb,
  data_table_name      varchar(100),
  loop_mode            char(1)        default '0',
  update_mode          char(1)        default '0',
  unique_key_fields    text,
  status               char(1)        default '0',
  create_by            varchar(64)    default '',
  create_time          timestamp(0),
  update_by            varchar(64)    default '',
  update_time          timestamp(0),
  remark               varchar(500)   default '',
  primary key (step_id)
);
create index idx_workflow_id_step on tushare_workflow_step(workflow_id);
create index idx_config_id_step on tushare_workflow_step(config_id);
create unique index uk_workflow_step_order on tushare_workflow_step(workflow_id, step_order);
comment on column tushare_workflow_step.step_id is '姝ラID';
comment on column tushare_workflow_step.workflow_id is '娴佺▼ID';
comment on column tushare_workflow_step.step_order is '姝ラ椤哄簭锛堜粠1寮€濮嬶級';
comment on column tushare_workflow_step.step_name is '姝ラ鍚嶇О';
comment on column tushare_workflow_step.config_id is '鎺ュ彛閰嶇疆ID';
comment on column tushare_workflow_step.step_params is '姝ラ鍙傛暟锛圝SON鏍煎紡锛屽彲浠庡墠涓€姝ヨ幏鍙栨暟鎹級';
comment on column tushare_workflow_step.condition_expr is '鎵ц鏉′欢锛圝SON鏍煎紡锛屽彲閫夛級';
comment on column tushare_workflow_step.position_x is '鑺傜偣X鍧愭爣锛堢敤浜庡彲瑙嗗寲甯冨眬锛?;
comment on column tushare_workflow_step.position_y is '鑺傜偣Y鍧愭爣锛堢敤浜庡彲瑙嗗寲甯冨眬锛?;
comment on column tushare_workflow_step.node_type is '鑺傜偣绫诲瀷锛坰tart/end/task锛?;
comment on column tushare_workflow_step.source_step_ids is '鍓嶇疆姝ラID鍒楄〃锛圝SON鏍煎紡锛屾敮鎸佸涓墠缃妭鐐癸級';
comment on column tushare_workflow_step.target_step_ids is '鍚庣疆姝ラID鍒楄〃锛圝SON鏍煎紡锛屾敮鎸佸涓悗缃妭鐐癸級';
comment on column tushare_workflow_step.layout_data is '瀹屾暣鐨勫竷灞€鏁版嵁锛圝SONB鏍煎紡锛屽瓨鍌ㄨ妭鐐逛綅缃€佽繛鎺ョ嚎绛夊彲瑙嗗寲淇℃伅锛?;
comment on column tushare_workflow_step.data_table_name is '鏁版嵁瀛樺偍琛ㄥ悕锛堜负绌哄垯浣跨敤浠诲姟閰嶇疆鐨勮〃鍚嶆垨榛樿琛ㄥ悕锛?;
comment on column tushare_workflow_step.loop_mode is '閬嶅巻妯″紡锛?鍚?1鏄紝寮€鍚悗鎵€鏈夊彉閲忓弬鏁伴兘浼氶亶鍘嗭級';
comment on column tushare_workflow_step.update_mode is '鏁版嵁鏇存柊鏂瑰紡锛?浠呮彃鍏?1蹇界暐閲嶅 2瀛樺湪鍒欐洿鏂?3鍏堝垹闄ゅ啀鎻掑叆锛?;
comment on column tushare_workflow_step.unique_key_fields is '鍞竴閿瓧娈甸厤缃紙JSON鏍煎紡锛屼负绌哄垯鑷姩妫€娴嬶級';
comment on column tushare_workflow_step.status is '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?;
comment on column tushare_workflow_step.create_by is '鍒涘缓鑰?;
comment on column tushare_workflow_step.create_time is '鍒涘缓鏃堕棿';
comment on column tushare_workflow_step.update_by is '鏇存柊鑰?;
comment on column tushare_workflow_step.update_time is '鏇存柊鏃堕棿';
comment on column tushare_workflow_step.remark is '澶囨敞淇℃伅';
comment on table tushare_workflow_step is 'Tushare娴佺▼姝ラ琛?;

-- ========== 2. 鑿滃崟 ==========

-- 涓昏彍鍗曪細Tushare鏁版嵁绠＄悊
insert into sys_menu values(2000, 'Tushare鏁版嵁绠＄悊', 0, 5, 'tushare', null, '', '', 1, 0, 'M', '0', '0', '', 'guide', 'admin', current_timestamp, '', null, 'Tushare鏁版嵁绠＄悊鐩綍');

-- 浜岀骇鑿滃崟锛氭帴鍙ｉ厤缃鐞?
insert into sys_menu values(2001, '鎺ュ彛閰嶇疆', 2000, 1, 'apiconfig', 'tushare/apiconfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:apiConfig:list', 'list', 'admin', current_timestamp, '', null, 'Tushare鎺ュ彛閰嶇疆鑿滃崟');

-- 浜岀骇鑿滃崟锛氫笅杞戒换鍔＄鐞?
insert into sys_menu values(2002, '涓嬭浇浠诲姟', 2000, 2, 'downloadTask', 'tushare/downloadTask/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadTask:list', 'job', 'admin', current_timestamp, '', null, 'Tushare涓嬭浇浠诲姟鑿滃崟');

-- 浜岀骇鑿滃崟锛氫笅杞芥棩蹇?
insert into sys_menu values(2003, '涓嬭浇鏃ュ織', 2000, 3, 'downloadLog', 'tushare/downloadLog/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadLog:list', 'log', 'admin', current_timestamp, '', null, 'Tushare涓嬭浇鏃ュ織鑿滃崟');

-- 鎺ュ彛閰嶇疆鎸夐挳
insert into sys_menu values(2100, '鎺ュ彛閰嶇疆鏌ヨ', 2001, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2101, '鎺ュ彛閰嶇疆鏂板', 2001, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2102, '鎺ュ彛閰嶇疆淇敼', 2001, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2103, '鎺ュ彛閰嶇疆鍒犻櫎', 2001, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2104, '鎺ュ彛閰嶇疆瀵煎嚭', 2001, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:export', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2105, '鎺ュ彛閰嶇疆鐘舵€佷慨鏀?, 2001, 6, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:changeStatus', '#', 'admin', current_timestamp, '', null, '');

-- 涓嬭浇浠诲姟鎸夐挳
insert into sys_menu values(2110, '涓嬭浇浠诲姟鏌ヨ', 2002, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2111, '涓嬭浇浠诲姟鏂板', 2002, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2112, '涓嬭浇浠诲姟淇敼', 2002, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2113, '涓嬭浇浠诲姟鍒犻櫎', 2002, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2114, '涓嬭浇浠诲姟鐘舵€佷慨鏀?, 2002, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:changeStatus', '#', 'admin', current_timestamp, '', null, '');

-- 涓嬭浇鏃ュ織鎸夐挳
insert into sys_menu values(2120, '涓嬭浇鏃ュ織鏌ヨ', 2003, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2121, '涓嬭浇鏃ュ織鍒犻櫎', 2003, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:remove', '#', 'admin', current_timestamp, '', null, '');

-- 浜岀骇鑿滃崟锛氭祦绋嬮厤缃鐞?
insert into sys_menu values(2004, '娴佺▼閰嶇疆', 2000, 4, 'workflowConfig', 'tushare/workflowConfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:workflowConfig:list', 'tree', 'admin', current_timestamp, '', null, 'Tushare娴佺▼閰嶇疆鑿滃崟');

-- 浜岀骇鑿滃崟锛氭祦绋嬫楠ょ鐞?
insert into sys_menu values(2005, '娴佺▼姝ラ', 2000, 5, 'workflowStep', 'tushare/workflowStep/index', '', '', 1, 0, 'C', '0', '0', 'tushare:workflowStep:list', 'tree-table', 'admin', current_timestamp, '', null, 'Tushare娴佺▼姝ラ鑿滃崟');

-- 娴佺▼閰嶇疆鎸夐挳
insert into sys_menu values(2130, '娴佺▼閰嶇疆鏌ヨ', 2004, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2131, '娴佺▼閰嶇疆鏂板', 2004, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2132, '娴佺▼閰嶇疆淇敼', 2004, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2133, '娴佺▼閰嶇疆鍒犻櫎', 2004, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:remove', '#', 'admin', current_timestamp, '', null, '');

-- 娴佺▼姝ラ鎸夐挳
insert into sys_menu values(2140, '娴佺▼姝ラ鏌ヨ', 2005, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2141, '娴佺▼姝ラ鏂板', 2005, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2142, '娴佺▼姝ラ淇敼', 2005, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(2143, '娴佺▼姝ラ鍒犻櫎', 2005, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:remove', '#', 'admin', current_timestamp, '', null, '');

-- 涓嬭浇浠诲姟鎵ц鎸夐挳锛堣ˉ鍏咃級
insert into sys_menu values(2115, '涓嬭浇浠诲姟鎵ц', 2002, 6, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:execute', '#', 'admin', current_timestamp, '', null, '');

-- ========== 3. 杩愯琛?==========

-- ----------------------------
-- Tushare涓嬭浇浠诲姟杩愯琛紙杩愯鎬昏锛? PostgreSQL 鐗堟湰
-- 涓?MySQL 鐗?tushare_download_run.sql 瀛楁淇濇寔涓€鑷?
-- ----------------------------
DROP TABLE IF EXISTS tushare_download_run;

CREATE TABLE tushare_download_run (
  run_id          BIGSERIAL     PRIMARY KEY,                    -- 杩愯ID
  task_id         BIGINT        NOT NULL,                       -- 浠诲姟ID
  task_name       VARCHAR(100)  NOT NULL,                       -- 浠诲姟鍚嶇О蹇収
  status          VARCHAR(20)   NOT NULL,                       -- 杩愯鐘舵€侊紙PENDING/RUNNING/SUCCESS/FAILED/CANCELED/TIMEOUT锛?
  start_time      TIMESTAMP,                                   -- 寮€濮嬫椂闂?
  end_time        TIMESTAMP,                                   -- 缁撴潫鏃堕棿
  progress        INTEGER       DEFAULT 0,                      -- 杩涘害锛?-100锛?
  total_records   INTEGER       DEFAULT 0,                      -- 鏈澶勭悊鎬昏褰曟暟
  success_records INTEGER       DEFAULT 0,                      -- 鎴愬姛璁板綍鏁?
  fail_records    INTEGER       DEFAULT 0,                      -- 澶辫触璁板綍鏁?
  error_message   TEXT,                                         -- 閿欒淇℃伅
  create_time     TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,      -- 鍒涘缓鏃堕棿
  update_time     TIMESTAMP                                     -- 鏇存柊鏃堕棿
);

CREATE INDEX idx_task_id_run    ON tushare_download_run (task_id);
CREATE INDEX idx_status_run     ON tushare_download_run (status);
CREATE INDEX idx_start_time_run ON tushare_download_run (start_time);
CREATE INDEX idx_end_time_run   ON tushare_download_run (end_time);

COMMENT ON TABLE  tushare_download_run IS 'Tushare涓嬭浇浠诲姟杩愯琛紙杩愯鎬昏锛?;
COMMENT ON COLUMN tushare_download_run.run_id          IS '杩愯ID';
COMMENT ON COLUMN tushare_download_run.task_id         IS '浠诲姟ID';
COMMENT ON COLUMN tushare_download_run.task_name       IS '浠诲姟鍚嶇О蹇収';
COMMENT ON COLUMN tushare_download_run.status          IS '杩愯鐘舵€侊紙PENDING/RUNNING/SUCCESS/FAILED/CANCELED/TIMEOUT锛?;
COMMENT ON COLUMN tushare_download_run.start_time      IS '寮€濮嬫椂闂?;
COMMENT ON COLUMN tushare_download_run.end_time        IS '缁撴潫鏃堕棿';
COMMENT ON COLUMN tushare_download_run.progress        IS '杩涘害锛?-100锛?;
COMMENT ON COLUMN tushare_download_run.total_records   IS '鏈澶勭悊鎬昏褰曟暟';
COMMENT ON COLUMN tushare_download_run.success_records IS '鎴愬姛璁板綍鏁?;
COMMENT ON COLUMN tushare_download_run.fail_records    IS '澶辫触璁板綍鏁?;
COMMENT ON COLUMN tushare_download_run.error_message   IS '閿欒淇℃伅';
COMMENT ON COLUMN tushare_download_run.create_time     IS '鍒涘缓鏃堕棿';
COMMENT ON COLUMN tushare_download_run.update_time     IS '鏇存柊鏃堕棿';

