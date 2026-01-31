-- ----------------------------
-- Tushare妯″潡锛圡ySQL锛夛細琛ㄧ粨鏋?+ 鑿滃崟 + 杩愯琛?-- 鏂扮幆澧冩墽琛屾湰鏂囦欢鍗冲彲锛涙棫搴撳崌绾ц migrations_mysql.sql
-- ----------------------------
-- ========== 1. 琛ㄧ粨鏋?==========
-- ----------------------------
-- Tushare鏁版嵁涓嬭浇妯″潡鐩稿叧琛?-- ----------------------------

-- ----------------------------
-- 1銆乀ushare鎺ュ彛閰嶇疆琛?-- ----------------------------
drop table if exists tushare_api_config;
create table tushare_api_config (
  config_id           bigint(20)      not null auto_increment    comment '閰嶇疆ID',
  api_name            varchar(100)    not null                    comment '鎺ュ彛鍚嶇О',
  api_code            varchar(100)    not null                    comment '鎺ュ彛浠ｇ爜锛堝锛歴tock_basic锛?,
  api_desc            text                                        comment '鎺ュ彛鎻忚堪',
  api_params          text                                        comment '鎺ュ彛鍙傛暟锛圝SON鏍煎紡锛?,
  data_fields         text                                        comment '鏁版嵁瀛楁锛圝SON鏍煎紡锛岀敤浜庢寚瀹氶渶瑕佷笅杞界殑瀛楁锛?,
  primary_key_fields  text                                        comment '涓婚敭瀛楁閰嶇疆锛圝SON鏍煎紡锛屼负绌哄垯浣跨敤榛樿data_id涓婚敭锛?,
  status              char(1)         default '0'                 comment '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?,
  create_by           varchar(64)     default ''                  comment '鍒涘缓鑰?,
  create_time         datetime                                     comment '鍒涘缓鏃堕棿',
  update_by           varchar(64)     default ''                  comment '鏇存柊鑰?,
  update_time         datetime                                     comment '鏇存柊鏃堕棿',
  remark              varchar(500)    default ''                  comment '澶囨敞淇℃伅',
  primary key (config_id),
  unique key uk_api_code (api_code)
) engine=innodb auto_increment=1 comment = 'Tushare鎺ュ彛閰嶇疆琛?;

-- ----------------------------
-- 2銆乀ushare涓嬭浇浠诲姟琛?-- ----------------------------
drop table if exists tushare_download_task;
create table tushare_download_task (
  task_id             bigint(20)      not null auto_increment    comment '浠诲姟ID',
  task_name           varchar(100)    not null                    comment '浠诲姟鍚嶇О',
  config_id           bigint(20)      not null                    comment '鎺ュ彛閰嶇疆ID',
  cron_expression     varchar(255)                                comment 'cron鎵ц琛ㄨ揪寮?,
  start_date          varchar(20)                                 comment '寮€濮嬫棩鏈燂紙YYYYMMDD锛?,
  end_date            varchar(20)                                 comment '缁撴潫鏃ユ湡锛圷YYYMMDD锛?,
  task_params         text                                        comment '浠诲姟鍙傛暟锛圝SON鏍煎紡锛岃鐩栨帴鍙ｉ粯璁ゅ弬鏁帮級',
  save_path           varchar(500)                                 comment '淇濆瓨璺緞',
  save_format         varchar(20)     default 'csv'              comment '淇濆瓨鏍煎紡锛坈sv/excel/json锛?,
  save_to_db          char(1)         default '0'                 comment '鏄惁淇濆瓨鍒版暟鎹簱锛?鍚?1鏄級',
  data_table_name     varchar(100)                                comment '鏁版嵁瀛樺偍琛ㄥ悕锛堜负绌哄垯浣跨敤榛樿琛╰ushare_data锛?,
  status              char(1)         default '0'                 comment '鐘舵€侊紙0姝ｅ父 1鏆傚仠锛?,
  last_run_time       datetime                                     comment '鏈€鍚庤繍琛屾椂闂?,
  next_run_time       datetime                                     comment '涓嬫杩愯鏃堕棿',
  run_count           int(11)         default 0                   comment '杩愯娆℃暟',
  success_count       int(11)         default 0                   comment '鎴愬姛娆℃暟',
  fail_count          int(11)         default 0                   comment '澶辫触娆℃暟',
  create_by           varchar(64)     default ''                  comment '鍒涘缓鑰?,
  create_time         datetime                                     comment '鍒涘缓鏃堕棿',
  update_by           varchar(64)     default ''                  comment '鏇存柊鑰?,
  update_time         datetime                                     comment '鏇存柊鏃堕棿',
  remark              varchar(500)    default ''                  comment '澶囨敞淇℃伅',
  primary key (task_id),
  unique key uk_task_name (task_name),
  key idx_config_id (config_id)
) engine=innodb auto_increment=1 comment = 'Tushare涓嬭浇浠诲姟琛?;

-- ----------------------------
-- 3銆乀ushare涓嬭浇鏃ュ織琛?-- ----------------------------
drop table if exists tushare_download_log;
create table tushare_download_log (
  log_id              bigint(20)      not null auto_increment    comment '鏃ュ織ID',
  task_id             bigint(20)      not null                    comment '浠诲姟ID',
  task_name           varchar(100)    not null                    comment '浠诲姟鍚嶇О',
  config_id           bigint(20)      not null                    comment '鎺ュ彛閰嶇疆ID',
  api_name            varchar(100)    not null                    comment '鎺ュ彛鍚嶇О',
  download_date       varchar(20)                                 comment '涓嬭浇鏃ユ湡锛圷YYYMMDD锛?,
  record_count        int(11)         default 0                   comment '璁板綍鏁?,
  file_path           varchar(500)                                 comment '鏂囦欢璺緞',
  status              char(1)         default '0'                 comment '鎵ц鐘舵€侊紙0鎴愬姛 1澶辫触锛?,
  error_message       text                                        comment '閿欒淇℃伅',
  duration            int(11)                                     comment '鎵ц鏃堕暱锛堢锛?,
  create_time         datetime                                     comment '鍒涘缓鏃堕棿',
  primary key (log_id),
  key idx_task_id (task_id),
  key idx_config_id (config_id),
  key idx_create_time (create_time)
) engine=innodb auto_increment=1 comment = 'Tushare涓嬭浇鏃ュ織琛?;

-- ----------------------------
-- 4銆乀ushare鏁版嵁瀛樺偍琛紙閫氱敤琛紝浣跨敤JSON瀛樺偍鐏垫椿鏁版嵁锛?-- ----------------------------
drop table if exists tushare_data;
create table tushare_data (
  data_id             bigint(20)      not null auto_increment    comment '鏁版嵁ID',
  task_id             bigint(20)      not null                    comment '浠诲姟ID',
  config_id           bigint(20)      not null                    comment '鎺ュ彛閰嶇疆ID',
  api_code          varchar(100)    not null                    comment '鎺ュ彛浠ｇ爜',
  download_date       varchar(20)                                 comment '涓嬭浇鏃ユ湡锛圷YYYMMDD锛?,
  data_content        json                                        comment '鏁版嵁鍐呭锛圝SON鏍煎紡锛?,
  create_time         datetime        default current_timestamp  comment '鍒涘缓鏃堕棿',
  primary key (data_id),
  key idx_task_id_data (task_id),
  key idx_config_id_data (config_id),
  key idx_api_code_data (api_code),
  key idx_download_date_data (download_date),
  key idx_create_time_data (create_time)
) engine=innodb auto_increment=1 comment = 'Tushare鏁版嵁瀛樺偍琛紙閫氱敤琛級';

-- ----------------------------
-- 5銆乀ushare娴佺▼閰嶇疆琛?-- ----------------------------
drop table if exists tushare_workflow_config;
create table tushare_workflow_config (
  workflow_id          bigint(20)      not null auto_increment    comment '娴佺▼ID',
  workflow_name        varchar(100)    not null                    comment '娴佺▼鍚嶇О',
  workflow_desc        text                                        comment '娴佺▼鎻忚堪',
  status               char(1)         default '0'                 comment '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?,
  create_by            varchar(64)     default ''                  comment '鍒涘缓鑰?,
  create_time          datetime                                     comment '鍒涘缓鏃堕棿',
  update_by            varchar(64)     default ''                  comment '鏇存柊鑰?,
  update_time          datetime                                     comment '鏇存柊鏃堕棿',
  remark               varchar(500)    default ''                  comment '澶囨敞淇℃伅',
  primary key (workflow_id),
  unique key uk_workflow_name (workflow_name)
) engine=innodb auto_increment=1 comment = 'Tushare娴佺▼閰嶇疆琛?;

-- ----------------------------
-- 6銆乀ushare娴佺▼姝ラ琛?-- ----------------------------
drop table if exists tushare_workflow_step;
create table tushare_workflow_step (
  step_id              bigint(20)      not null auto_increment    comment '姝ラID',
  workflow_id          bigint(20)      not null                    comment '娴佺▼ID',
  step_order           int(11)         not null                    comment '姝ラ椤哄簭锛堜粠1寮€濮嬶級',
  step_name            varchar(100)    not null                    comment '姝ラ鍚嶇О',
  config_id            bigint(20)      not null                    comment '鎺ュ彛閰嶇疆ID',
  step_params          text                                        comment '姝ラ鍙傛暟锛圝SON鏍煎紡锛屽彲浠庡墠涓€姝ヨ幏鍙栨暟鎹級',
  condition_expr       text                                        comment '鎵ц鏉′欢锛圝SON鏍煎紡锛屽彲閫夛級',
  status               char(1)         default '0'                 comment '鐘舵€侊紙0姝ｅ父 1鍋滅敤锛?,
  create_by            varchar(64)     default ''                  comment '鍒涘缓鑰?,
  create_time          datetime                                     comment '鍒涘缓鏃堕棿',
  update_by            varchar(64)     default ''                  comment '鏇存柊鑰?,
  update_time          datetime                                     comment '鏇存柊鏃堕棿',
  remark               varchar(500)    default ''                  comment '澶囨敞淇℃伅',
  primary key (step_id),
  key idx_workflow_id (workflow_id),
  key idx_config_id (config_id),
  unique key uk_workflow_step_order (workflow_id, step_order)
) engine=innodb auto_increment=1 comment = 'Tushare娴佺▼姝ラ琛?;

-- ----------------------------
-- 淇敼涓嬭浇浠诲姟琛紝娣诲姞娴佺▼閰嶇疆鏀寔
-- ----------------------------
alter table tushare_download_task add column workflow_id bigint(20) comment '娴佺▼閰嶇疆ID锛堝鏋滃瓨鍦ㄥ垯鎵ц娴佺▼锛屽惁鍒欐墽琛屽崟涓帴鍙ｏ級';
create index idx_workflow_id_task on tushare_download_task(workflow_id);

-- ----------------------------
-- 淇敼涓嬭浇浠诲姟琛紝娣诲姞浠诲姟绫诲瀷瀛楁
-- ----------------------------
alter table tushare_download_task add column task_type varchar(20) default 'single' comment '浠诲姟绫诲瀷锛坰ingle:鍗曚釜鎺ュ彛 workflow:娴佺▼閰嶇疆锛?;
create index idx_task_type on tushare_download_task(task_type);

-- ----------------------------
-- 淇敼涓嬭浇浠诲姟琛紝鍏佽config_id涓虹┖锛堟祦绋嬮厤缃ā寮忎笅鍙互涓虹┖锛?-- ----------------------------
alter table tushare_download_task modify column config_id bigint(20) null comment '鎺ュ彛閰嶇疆ID';

-- ----------------------------
-- 鎵╁睍娴佺▼姝ラ琛紝娣诲姞鍙鍖栫紪杈戝櫒鏀寔瀛楁
-- ----------------------------
alter table tushare_workflow_step add column position_x int(11) comment '鑺傜偣X鍧愭爣锛堢敤浜庡彲瑙嗗寲甯冨眬锛?;
alter table tushare_workflow_step add column position_y int(11) comment '鑺傜偣Y鍧愭爣锛堢敤浜庡彲瑙嗗寲甯冨眬锛?;
alter table tushare_workflow_step add column node_type varchar(20) default 'task' comment '鑺傜偣绫诲瀷锛坰tart/end/task锛?;
alter table tushare_workflow_step add column source_step_ids text comment '鍓嶇疆姝ラID鍒楄〃锛圝SON鏍煎紡锛屾敮鎸佸涓墠缃妭鐐癸級';
alter table tushare_workflow_step add column target_step_ids text comment '鍚庣疆姝ラID鍒楄〃锛圝SON鏍煎紡锛屾敮鎸佸涓悗缃妭鐐癸級';
alter table tushare_workflow_step add column layout_data json comment '瀹屾暣鐨勫竷灞€鏁版嵁锛圝SON鏍煎紡锛屽瓨鍌ㄨ妭鐐逛綅缃€佽繛鎺ョ嚎绛夊彲瑙嗗寲淇℃伅锛?;
alter table tushare_workflow_step add column data_table_name varchar(100) comment '鏁版嵁瀛樺偍琛ㄥ悕锛堜负绌哄垯浣跨敤浠诲姟閰嶇疆鐨勮〃鍚嶆垨榛樿琛ㄥ悕锛?;

-- ----------------------------
-- 鎵╁睍娴佺▼姝ラ琛紝娣诲姞閬嶅巻妯″紡鍜屾暟鎹洿鏂版柟寮忓瓧娈?-- ----------------------------
alter table tushare_workflow_step add column loop_mode char(1) default '0' comment '閬嶅巻妯″紡锛?鍚?1鏄紝寮€鍚悗鎵€鏈夊彉閲忓弬鏁伴兘浼氶亶鍘嗭級';
alter table tushare_workflow_step add column update_mode char(1) default '0' comment '鏁版嵁鏇存柊鏂瑰紡锛?浠呮彃鍏?1蹇界暐閲嶅 2瀛樺湪鍒欐洿鏂?3鍏堝垹闄ゅ啀鎻掑叆锛?;
alter table tushare_workflow_step add column unique_key_fields text comment '鍞竴閿瓧娈甸厤缃紙JSON鏍煎紡锛屼负绌哄垯鑷姩妫€娴嬶級';

-- ========== 2. 鑿滃崟 ==========

-- 涓昏彍鍗曪細Tushare鏁版嵁绠＄悊
insert into sys_menu values('2000', 'Tushare鏁版嵁绠＄悊', '0', '5', 'tushare', null, '', '', 1, 0, 'M', '0', '0', '', 'guide', 'admin', sysdate(), '', null, 'Tushare鏁版嵁绠＄悊鐩綍');

-- 浜岀骇鑿滃崟锛氭帴鍙ｉ厤缃鐞?
insert into sys_menu values('2001', '鎺ュ彛閰嶇疆', '2000', '1', 'apiconfig', 'tushare/apiconfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:apiConfig:list', 'list', 'admin', sysdate(), '', null, 'Tushare鎺ュ彛閰嶇疆鑿滃崟');

-- 浜岀骇鑿滃崟锛氫笅杞戒换鍔＄鐞?
insert into sys_menu values('2002', '涓嬭浇浠诲姟', '2000', '2', 'downloadTask', 'tushare/downloadTask/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadTask:list', 'job', 'admin', sysdate(), '', null, 'Tushare涓嬭浇浠诲姟鑿滃崟');

-- 浜岀骇鑿滃崟锛氫笅杞芥棩蹇?
insert into sys_menu values('2003', '涓嬭浇鏃ュ織', '2000', '3', 'downloadLog', 'tushare/downloadLog/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadLog:list', 'log', 'admin', sysdate(), '', null, 'Tushare涓嬭浇鏃ュ織鑿滃崟');

-- 鎺ュ彛閰嶇疆鎸夐挳
insert into sys_menu values('2100', '鎺ュ彛閰嶇疆鏌ヨ', '2001', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2101', '鎺ュ彛閰嶇疆鏂板', '2001', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2102', '鎺ュ彛閰嶇疆淇敼', '2001', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2103', '鎺ュ彛閰嶇疆鍒犻櫎', '2001', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2104', '鎺ュ彛閰嶇疆瀵煎嚭', '2001', '5', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:export', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2105', '鎺ュ彛閰嶇疆鐘舵€佷慨鏀?, '2001', '6', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:changeStatus', '#', 'admin', sysdate(), '', null, '');

-- 涓嬭浇浠诲姟鎸夐挳
insert into sys_menu values('2110', '涓嬭浇浠诲姟鏌ヨ', '2002', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2111', '涓嬭浇浠诲姟鏂板', '2002', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2112', '涓嬭浇浠诲姟淇敼', '2002', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2113', '涓嬭浇浠诲姟鍒犻櫎', '2002', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2114', '涓嬭浇浠诲姟鐘舵€佷慨鏀?, '2002', '5', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:changeStatus', '#', 'admin', sysdate(), '', null, '');

-- 涓嬭浇鏃ュ織鎸夐挳
insert into sys_menu values('2120', '涓嬭浇鏃ュ織鏌ヨ', '2003', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2121', '涓嬭浇鏃ュ織鍒犻櫎', '2003', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:remove', '#', 'admin', sysdate(), '', null, '');

-- 浜岀骇鑿滃崟锛氭祦绋嬮厤缃鐞?
insert into sys_menu values('2004', '娴佺▼閰嶇疆', '2000', '4', 'workflowConfig', 'tushare/workflowConfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:workflowConfig:list', 'tree', 'admin', sysdate(), '', null, 'Tushare娴佺▼閰嶇疆鑿滃崟');

-- 浜岀骇鑿滃崟锛氭祦绋嬫楠ょ鐞?
insert into sys_menu values('2005', '娴佺▼姝ラ', '2000', '5', 'workflowStep', 'tushare/workflowStep/index', '', '', 1, 0, 'C', '0', '0', 'tushare:workflowStep:list', 'tree-table', 'admin', sysdate(), '', null, 'Tushare娴佺▼姝ラ鑿滃崟');

-- 娴佺▼閰嶇疆鎸夐挳
insert into sys_menu values('2130', '娴佺▼閰嶇疆鏌ヨ', '2004', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2131', '娴佺▼閰嶇疆鏂板', '2004', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2132', '娴佺▼閰嶇疆淇敼', '2004', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2133', '娴佺▼閰嶇疆鍒犻櫎', '2004', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:remove', '#', 'admin', sysdate(), '', null, '');

-- 娴佺▼姝ラ鎸夐挳
insert into sys_menu values('2140', '娴佺▼姝ラ鏌ヨ', '2005', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2141', '娴佺▼姝ラ鏂板', '2005', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2142', '娴佺▼姝ラ淇敼', '2005', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('2143', '娴佺▼姝ラ鍒犻櫎', '2005', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:remove', '#', 'admin', sysdate(), '', null, '');

-- 涓嬭浇浠诲姟鎵ц鎸夐挳锛堣ˉ鍏咃級
insert into sys_menu values('2115', '涓嬭浇浠诲姟鎵ц', '2002', '6', '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:execute', '#', 'admin', sysdate(), '', null, '');

-- ========== 3. 杩愯琛?==========

-- ----------------------------
-- Tushare涓嬭浇浠诲姟杩愯琛紙杩愯鎬昏锛?
-- 閲囩敤鏂规B锛氬皢杩愯缁村害浠庢棩蹇椾腑鎷嗗垎鍑烘潵
-- ----------------------------
drop table if exists tushare_download_run;
create table tushare_download_run (
  run_id            bigint(20)      not null auto_increment    comment '杩愯ID',
  task_id           bigint(20)      not null                   comment '浠诲姟ID',
  task_name         varchar(100)    not null                   comment '浠诲姟鍚嶇О蹇収',
  status            varchar(20)     not null                   comment '杩愯鐘舵€侊紙PENDING/RUNNING/SUCCESS/FAILED/CANCELED/TIMEOUT锛?,
  start_time        datetime                                   comment '寮€濮嬫椂闂?,
  end_time          datetime                                   comment '缁撴潫鏃堕棿',
  progress          int(11)         default 0                  comment '杩涘害锛?-100锛?,
  total_records     int(11)         default 0                  comment '鏈澶勭悊鎬昏褰曟暟',
  success_records   int(11)         default 0                  comment '鎴愬姛璁板綍鏁?,
  fail_records      int(11)         default 0                  comment '澶辫触璁板綍鏁?,
  error_message     text                                       comment '閿欒淇℃伅',
  create_time       datetime        default current_timestamp comment '鍒涘缓鏃堕棿',
  update_time       datetime                                   comment '鏇存柊鏃堕棿',
  primary key (run_id),
  key idx_task_id_run (task_id),
  key idx_status_run (status),
  key idx_start_time_run (start_time),
  key idx_end_time_run (end_time)
) engine=innodb auto_increment=1 comment = 'Tushare涓嬭浇浠诲姟杩愯琛紙杩愯鎬昏锛?;

