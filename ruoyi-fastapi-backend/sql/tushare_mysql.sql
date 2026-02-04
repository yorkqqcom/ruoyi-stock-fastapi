-- ----------------------------
-- Tushare模块（MySQL）：表结构 + 菜单 + 运行表
-- 新环境执行本文件即可；旧库升级见 migrations_mysql.sql
-- ----------------------------
-- ========== 1. 表结构 ==========
-- ----------------------------
-- 1、Tushare接口配置表
-- ----------------------------
drop table if exists tushare_api_config;
create table tushare_api_config (
  config_id           bigint(20)      not null auto_increment    comment '配置ID',
  api_name            varchar(100)    not null                    comment '接口名称',
  api_code            varchar(100)    not null                    comment '接口代码（如：stock_basic）',
  api_desc            text                                        comment '接口描述',
  api_params          text                                        comment '接口参数（JSON格式）',
  data_fields         text                                        comment '数据字段（JSON格式，用于指定需要下载的字段）',
  primary_key_fields  text                                        comment '主键字段配置（JSON格式，为空则使用默认data_id主键）',
  status              char(1)         default '0'                 comment '状态（0正常 1停用）',
  create_by           varchar(64)     default ''                  comment '创建者',
  create_time         datetime                                     comment '创建时间',
  update_by           varchar(64)     default ''                  comment '更新者',
  update_time         datetime                                     comment '更新时间',
  remark              varchar(500)    default ''                  comment '备注信息',
  primary key (config_id),
  unique key uk_api_code (api_code)
) engine=innodb auto_increment=1 comment = 'Tushare接口配置表';

INSERT INTO tushare_api_config (api_name,api_code,api_desc,api_params,data_fields,status,create_by,create_time,update_by,update_time,remark,primary_key_fields) VALUES
	 ('trade_cal','trade_cal','获取各大交易所交易日历数据,默认提取的是上交所','{"exchange": "SSE"}',NULL,'0','admin','2026-01-25 11:24:36','admin','2026-01-25 11:24:36','',NULL),
	 ('pro_bar','pro_bar','复权行情通过通用行情接口实现，利用Tushare Pro提供的复权因子进行动态计算，因此http方式无法调取。若需要静态复权行情（支持http），请访问股票技术因子接口。',NULL,NULL,'0','admin','2026-01-26 14:25:24','admin','2026-01-26 20:37:14','','["ts_code", "trade_date"]'),
	 ('stock_basic','stock_basic','获取基础信息数据，包括股票代码、名称、上市日期、退市日期等','{"list_status": "L"}',NULL,'0','admin','2026-01-24 21:17:16','admin','2026-01-26 20:46:09','','["ts_code"]'),
	 ('daily_basic','daily_basic','获取全部股票每日重要的基本面指标，可用于选股分析、报表展示等。单次请求最大返回6000条数据，可按日线循环提取全部历史。','{"trade_date": "today"}',NULL,'0','admin','2026-01-27 16:56:13','admin','2026-01-27 17:57:34','','["ts_code"]'),
	 ('daily','daily','获取股票行情数据，或通过通用行情接口获取数据，包含了前后复权数据','{"trade_date": "today"}',NULL,'0','admin','2026-01-27 18:03:05','admin','2026-01-27 18:03:05','','');

-- ----------------------------
-- 2、Tushare下载任务表
-- ----------------------------
drop table if exists tushare_download_task;
create table tushare_download_task (
  task_id             bigint(20)      not null auto_increment    comment '任务ID',
  task_name           varchar(100)    not null                    comment '任务名称',
  config_id           bigint(20)                                   comment '接口配置ID（流程配置模式下可以为空）',
  workflow_id         bigint(20)                                   comment '流程配置ID（如果存在则执行流程，否则执行单个接口）',
  task_type           varchar(20)     default 'single'            comment '任务类型（single:单个接口 workflow:流程配置）',
  cron_expression     varchar(255)                                comment 'cron执行表达式',
  start_date          varchar(20)                                 comment '开始日期（YYYYMMDD）',
  end_date            varchar(20)                                 comment '结束日期（YYYYMMDD）',
  task_params         text                                        comment '任务参数（JSON格式，覆盖接口默认参数）',
  save_path           varchar(500)                                 comment '保存路径',
  save_format         varchar(20)     default 'csv'              comment '保存格式（csv/excel/json）',
  save_to_db          char(1)         default '0'                 comment '是否保存到数据库（0否 1是）',
  data_table_name     varchar(100)                                comment '数据存储表名（为空则使用默认表tushare_data）',
  status              char(1)         default '0'                 comment '状态（0正常 1暂停）',
  last_run_time       datetime                                     comment '最后运行时间',
  next_run_time       datetime                                     comment '下次运行时间',
  run_count           int(11)         default 0                   comment '运行次数',
  success_count       int(11)         default 0                   comment '成功次数',
  fail_count          int(11)         default 0                   comment '失败次数',
  create_by           varchar(64)     default ''                  comment '创建者',
  create_time         datetime                                     comment '创建时间',
  update_by           varchar(64)     default ''                  comment '更新者',
  update_time         datetime                                     comment '更新时间',
  remark              varchar(500)    default ''                  comment '备注信息',
  primary key (task_id),
  unique key uk_task_name (task_name),
  key idx_config_id (config_id),
  key idx_workflow_id_task (workflow_id),
  key idx_task_type (task_type)
) engine=innodb auto_increment=1 comment = 'Tushare下载任务表';

INSERT INTO tushare_download_task (task_name,config_id,cron_expression,start_date,end_date,task_params,save_path,save_format,save_to_db,data_table_name,status,last_run_time,next_run_time,run_count,success_count,fail_count,create_by,create_time,update_by,update_time,remark,workflow_id,task_type) VALUES
	 ('历史行情下载',NULL,NULL,'20260123',NULL,NULL,NULL,'csv','1',NULL,'0','2026-01-28 16:20:06',NULL,1,1,0,'admin','2026-01-28 15:37:46','admin','2026-01-28 15:37:46','',4,'workflow'),
	 ('测试用',NULL,NULL,'20260123',NULL,NULL,NULL,'csv','1',NULL,'0','2026-01-28 22:35:38',NULL,5,5,0,'admin','2026-01-27 17:15:51','admin','2026-01-27 17:15:51','',1,'workflow'),
	 ('每日18点调度',NULL,'0 30 18 ? * MON-FRI','20260123',NULL,NULL,NULL,'csv','1',NULL,'0','2026-02-01 18:47:38',NULL,19,19,0,'admin','2026-01-26 10:46:23','admin','2026-01-27 18:05:40','',2,'workflow');

-- ----------------------------
-- 3、Tushare下载日志表
-- ----------------------------
drop table if exists tushare_download_log;
create table tushare_download_log (
  log_id              bigint(20)      not null auto_increment    comment '日志ID',
  task_id             bigint(20)      not null                    comment '任务ID',
  task_name           varchar(100)    not null                    comment '任务名称',
  config_id           bigint(20)      not null                    comment '接口配置ID',
  api_name            varchar(100)    not null                    comment '接口名称',
  download_date       varchar(20)                                 comment '下载日期（YYYYMMDD）',
  record_count        int(11)         default 0                   comment '记录数',
  file_path           varchar(500)                                 comment '文件路径',
  status              char(1)         default '0'                 comment '执行状态（0成功 1失败）',
  error_message       text                                        comment '错误信息',
  duration            int(11)                                     comment '执行时长（秒）',
  create_time         datetime                                     comment '创建时间',
  primary key (log_id),
  key idx_task_id (task_id),
  key idx_config_id (config_id),
  key idx_create_time (create_time)
) engine=innodb auto_increment=1 comment = 'Tushare下载日志表';

-- ----------------------------
-- 4、Tushare数据存储表（通用表，使用JSON存储灵活数据）
-- ----------------------------
drop table if exists tushare_data;
create table tushare_data (
  data_id             bigint(20)      not null auto_increment    comment '数据ID',
  task_id             bigint(20)      not null                    comment '任务ID',
  config_id           bigint(20)      not null                    comment '接口配置ID',
  api_code            varchar(100)    not null                    comment '接口代码',
  download_date       varchar(20)                                 comment '下载日期（YYYYMMDD）',
  data_content        json                                        comment '数据内容（JSON格式）',
  create_time         datetime        default current_timestamp  comment '创建时间',
  primary key (data_id),
  key idx_task_id_data (task_id),
  key idx_config_id_data (config_id),
  key idx_api_code_data (api_code),
  key idx_download_date_data (download_date),
  key idx_create_time_data (create_time)
) engine=innodb auto_increment=1 comment = 'Tushare数据存储表（通用表）';

-- ----------------------------
-- 5、Tushare流程配置表
-- ----------------------------
drop table if exists tushare_workflow_config;
create table tushare_workflow_config (
  workflow_id          bigint(20)      not null auto_increment    comment '流程ID',
  workflow_name        varchar(100)    not null                    comment '流程名称',
  workflow_desc        text                                        comment '流程描述',
  status               char(1)         default '0'                 comment '状态（0正常 1停用）',
  create_by            varchar(64)     default ''                  comment '创建者',
  create_time          datetime                                     comment '创建时间',
  update_by            varchar(64)     default ''                  comment '更新者',
  update_time          datetime                                     comment '更新时间',
  remark               varchar(500)    default ''                  comment '备注信息',
  primary key (workflow_id),
  unique key uk_workflow_name (workflow_name)
) engine=innodb auto_increment=1 comment = 'Tushare流程配置表';

INSERT INTO tushare_workflow_config (workflow_name,workflow_desc,status,create_by,create_time,update_by,update_time,remark) VALUES
	 ('测试用',NULL,'0','admin','2026-01-27 17:02:48','admin','2026-01-27 17:02:48',''),
	 ('每日18点更新',NULL,'0','admin','2026-01-26 13:48:37','admin','2026-01-28 15:31:44',''),
	 ('每日16点更新','每日16点10分更新','0','admin','2026-01-27 18:03:56','admin','2026-01-28 15:31:55',''),
	 ('历史行情下载','历史行情下载','0','admin','2026-01-28 15:32:24','admin','2026-01-28 15:32:24','');

-- ----------------------------
-- 6、Tushare流程步骤表
-- ----------------------------
drop table if exists tushare_workflow_step;
create table tushare_workflow_step (
  step_id              bigint(20)      not null auto_increment    comment '步骤ID',
  workflow_id          bigint(20)      not null                    comment '流程ID',
  step_order           int(11)         not null                    comment '步骤顺序（从1开始）',
  step_name            varchar(100)    not null                    comment '步骤名称',
  config_id            bigint(20)      not null                    comment '接口配置ID',
  step_params          text                                        comment '步骤参数（JSON格式，可从前一步获取数据）',
  condition_expr       text                                        comment '执行条件（JSON格式，可选）',
  position_x           int(11)                                     comment '节点X坐标（用于可视化布局）',
  position_y           int(11)                                     comment '节点Y坐标（用于可视化布局）',
  node_type            varchar(20)     default 'task'             comment '节点类型（start/end/task）',
  source_step_ids      text                                        comment '前置步骤ID列表（JSON格式，支持多个前置节点）',
  target_step_ids      text                                        comment '后置步骤ID列表（JSON格式，支持多个后置节点）',
  layout_data          json                                        comment '完整的布局数据（JSON格式，存储节点位置、连接线等可视化信息）',
  data_table_name      varchar(100)                                comment '数据存储表名（为空则使用任务配置的表名或默认表名）',
  loop_mode            char(1)         default '0'                 comment '遍历模式（0否 1是，开启后所有变量参数都会遍历）',
  update_mode          char(1)         default '0'                 comment '数据更新方式（0仅插入 1忽略重复 2存在则更新 3先删除再插入）',
  unique_key_fields    text                                        comment '唯一键字段配置（JSON格式，为空则自动检测）',
  status               char(1)         default '0'                 comment '状态（0正常 1停用）',
  create_by            varchar(64)     default ''                  comment '创建者',
  create_time          datetime                                     comment '创建时间',
  update_by            varchar(64)     default ''                  comment '更新者',
  update_time          datetime                                     comment '更新时间',
  remark               varchar(500)    default ''                  comment '备注信息',
  primary key (step_id),
  key idx_workflow_id_step (workflow_id),
  key idx_config_id_step (config_id),
  unique key uk_workflow_step_order (workflow_id, step_order)
) engine=innodb auto_increment=1 comment = 'Tushare流程步骤表';

INSERT INTO tushare_workflow_step (workflow_id,step_order,step_name,config_id,step_params,condition_expr,position_x,position_y,node_type,source_step_ids,target_step_ids,layout_data,data_table_name,loop_mode,update_mode,unique_key_fields,status,create_by,create_time,update_by,update_time,remark) VALUES
	 (1,2,'任务节点',4,'{"trade_date": "today"}',NULL,172,79,'task',NULL,NULL,'null',NULL,'0','2',NULL,'0','admin','2026-01-27 17:15:31','admin','2026-01-27 17:15:31',''),
	 (1,3,'结束',0,NULL,NULL,498,77,'end',NULL,NULL,'null',NULL,'0','0',NULL,'0','admin','2026-01-27 17:15:31','admin','2026-01-27 17:15:31',''),
	 (3,1,'开始',0,NULL,NULL,14,68,'start',NULL,NULL,'{"edges": [{"id": "edge_node_1769508242813_node_1769508244669", "label": "", "source": "node_1769508242813", "target": "node_1769508244669", "sourceHandle": "right", "targetHandle": "target-left"}, {"id": "edge_node_1769508244669_node_1769508303164", "label": "", "source": "node_1769508244669", "target": "node_1769508303164", "sourceHandle": "source-right", "targetHandle": "left"}], "nodes": [{"id": "node_1769508242813", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "开始", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "start", "position": {"x": 13.894073486328125, "y": 68.06944274902344}}, {"id": "node_1769508244669", "data": {"stepId": null, "configId": 5, "loopMode": "0", "stepName": "任务节点", "stepParams": null, "updateMode": "1", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 231, "y": 69}}, {"id": "node_1769508303164", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "结束", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "end", "position": {"x": 540.8940734863281, "y": 64.06944274902344}}]}',NULL,'0','0',NULL,'0','admin','2026-01-27 18:05:11','admin','2026-01-27 18:05:11',''),
	 (3,2,'任务节点',5,NULL,NULL,231,69,'task',NULL,NULL,'null',NULL,'0','1',NULL,'0','admin','2026-01-27 18:05:11','admin','2026-01-27 18:05:11',''),
	 (3,3,'结束',0,NULL,NULL,541,64,'end',NULL,NULL,'null',NULL,'0','0',NULL,'0','admin','2026-01-27 18:05:11','admin','2026-01-27 18:05:11',''),
	 (1,1,'开始',0,NULL,NULL,11,63,'start',NULL,NULL,'{"edges": [{"id": "edge_node_1769504571587_node_1769504572758", "label": "", "source": "node_1769504571587", "target": "node_1769504572758", "sourceHandle": "right", "targetHandle": "target-left"}, {"id": "edge_node_1769504572758_node_1769504573846", "label": "", "source": "node_1769504572758", "target": "node_1769504573846", "sourceHandle": "source-right", "targetHandle": "left"}], "nodes": [{"id": "node_1769504571587", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "开始", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "start", "position": {"x": 10.894073486328125, "y": 63.06944274902344}}, {"id": "node_1769504572758", "data": {"stepId": null, "configId": 4, "loopMode": "0", "stepName": "任务节点", "stepParams": "{\"trade_date\": \"today\"}", "updateMode": "2", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 172, "y": 79}}, {"id": "node_1769504573846", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "结束", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "end", "position": {"x": 497.8940734863281, "y": 77.06944274902344}}]}',NULL,'0','0',NULL,'0','admin','2026-01-27 17:15:31','admin','2026-01-27 17:15:31',''),
	 (4,1,'开始',0,NULL,NULL,-6,98,'start',NULL,NULL,'{"edges": [{"id": "edge_node_1769585548611_node_1769585552211", "label": "", "source": "node_1769585548611", "target": "node_1769585552211", "sourceHandle": "right", "targetHandle": "target-left"}, {"id": "edge_node_1769585552211_node_1769585549763", "label": "", "source": "node_1769585552211", "target": "node_1769585549763", "sourceHandle": "source-right", "targetHandle": "source-left"}, {"id": "edge_node_1769585549763_node_1769585553462", "label": "", "source": "node_1769585549763", "target": "node_1769585553462", "sourceHandle": "source-right", "targetHandle": "left"}], "nodes": [{"id": "node_1769585548611", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "开始", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "start", "position": {"x": -6.105926513671875, "y": 98.06944274902344}}, {"id": "node_1769585549763", "data": {"stepId": null, "configId": 2, "loopMode": "0", "stepName": "任务节点", "stepParams": "{\"ts_code\": {\"type\": \"loop\", \"source\": \"previous_step.ts_code\"},\n\"start_date\":\"today-1000\",\n\"end_date\":\"today\",\n\"asset\":\"E\",\n\"adj\":\"hfq\",\n\"freq\":\"D\"\n}", "updateMode": "2", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 409, "y": 145}}, {"id": "node_1769585552211", "data": {"stepId": null, "configId": 3, "loopMode": "0", "stepName": "任务节点", "stepParams": null, "updateMode": "2", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 152, "y": 101}}, {"id": "node_1769585553462", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "结束", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "end", "position": {"x": 697.8940734863281, "y": 133.06944274902344}}]}',NULL,'0','0',NULL,'0','admin','2026-02-04 14:54:25','admin','2026-02-04 14:54:25',''),
	 (4,2,'任务节点',3,NULL,NULL,152,101,'task',NULL,NULL,'null',NULL,'0','2',NULL,'0','admin','2026-02-04 14:54:25','admin','2026-02-04 14:54:25',''),
	 (4,3,'任务节点',2,'{"ts_code": {"type": "loop", "source": "previous_step.ts_code"}, "start_date": "today-1000", "end_date": "today", "asset": "E", "adj": "hfq", "freq": "D"}',NULL,409,145,'task',NULL,NULL,'null',NULL,'0','2',NULL,'0','admin','2026-02-04 14:54:25','admin','2026-02-04 14:54:25',''),
	 (4,4,'结束',0,NULL,NULL,698,133,'end',NULL,NULL,'null',NULL,'0','0',NULL,'0','admin','2026-02-04 14:54:25','admin','2026-02-04 14:54:25','');
INSERT INTO tushare_workflow_step (workflow_id,step_order,step_name,config_id,step_params,condition_expr,position_x,position_y,node_type,source_step_ids,target_step_ids,layout_data,data_table_name,loop_mode,update_mode,unique_key_fields,status,create_by,create_time,update_by,update_time,remark) VALUES
	 (2,1,'开始',0,NULL,NULL,-155,189,'start',NULL,NULL,'{"edges": [{"id": "edge_node_1769408736947_node_1769409718154", "label": "", "source": "node_1769408736947", "target": "node_1769409718154", "sourceHandle": "source-right", "targetHandle": "target-left"}, {"id": "edge_node_1769409718154_node_1769409779167", "label": "", "source": "node_1769409718154", "target": "node_1769409779167", "sourceHandle": "source-right", "targetHandle": "left"}, {"id": "edge_node_1769408735542_node_1769504222367", "label": "", "source": "node_1769408735542", "target": "node_1769504222367", "sourceHandle": "right", "targetHandle": "target-left"}, {"id": "edge_node_1769504222367_node_1769408736947", "label": "", "source": "node_1769504222367", "target": "node_1769408736947", "sourceHandle": "source-right", "targetHandle": "target-left"}], "nodes": [{"id": "node_1769408735542", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "开始", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "start", "position": {"x": -154.84590526620963, "y": 188.65887667796719}}, {"id": "node_1769408736947", "data": {"stepId": null, "configId": 3, "loopMode": "0", "stepName": "任务节点", "stepParams": null, "updateMode": "3", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 288, "y": 35}}, {"id": "node_1769409718154", "data": {"stepId": null, "configId": 2, "loopMode": "0", "stepName": "任务节点", "stepParams": "{\"ts_code\": {\"type\": \"loop\", \"source\": \"previous_step.ts_code\"},\n\"start_date\":\"today\",\n\"end_date\":\"today\",\n\"asset\":\"E\",\n\"adj\":\"hfq\",\n\"freq\":\"D\"\n}", "updateMode": "1", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 618, "y": 39}}, {"id": "node_1769409779167", "data": {"stepId": null, "configId": null, "loopMode": "0", "stepName": "结束", "stepParams": null, "updateMode": "0", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "end", "position": {"x": 867.2548412026749, "y": 215.9440701688547}}, {"id": "node_1769504222367", "data": {"stepId": null, "configId": 4, "loopMode": "0", "stepName": "任务节点", "stepParams": "{\"trade_date\": \"today\"}", "updateMode": "2", "conditionExpr": null, "dataTableName": "", "uniqueKeyFields": null}, "type": "task", "position": {"x": 17.406331430384498, "y": 39.67249178857551}}]}',NULL,'0','0',NULL,'0','admin','2026-02-04 14:56:07','admin','2026-02-04 14:56:07',''),
	 (2,2,'任务节点',4,'{"trade_date": "today"}',NULL,17,40,'task',NULL,NULL,'null',NULL,'0','2',NULL,'0','admin','2026-02-04 14:56:07','admin','2026-02-04 14:56:07',''),
	 (2,3,'任务节点',3,NULL,NULL,288,35,'task',NULL,NULL,'null',NULL,'0','3',NULL,'0','admin','2026-02-04 14:56:07','admin','2026-02-04 14:56:07',''),
	 (2,4,'任务节点',2,'{"ts_code": {"type": "loop", "source": "previous_step.ts_code"}, "start_date": "today", "end_date": "today", "asset": "E", "adj": "hfq", "freq": "D"}',NULL,618,39,'task',NULL,NULL,'null',NULL,'0','1',NULL,'0','admin','2026-02-04 14:56:07','admin','2026-02-04 14:56:07',''),
	 (2,5,'结束',0,NULL,NULL,867,216,'end',NULL,NULL,'null',NULL,'0','0',NULL,'0','admin','2026-02-04 14:56:07','admin','2026-02-04 14:56:07','');


-- ========== 2. 菜单 ==========

-- 主菜单：Tushare数据管理
insert into sys_menu values(2000, 'Tushare数据管理', 0, 1, 'tushare', null, '', '', 1, 0, 'M', '0', '0', '', 'guide', 'admin', sysdate(), '', null, 'Tushare数据管理目录');

-- 二级菜单：接口配置管理
insert into sys_menu values(2001, '接口配置', 2000, 0, 'apiconfig', 'tushare/apiconfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:apiConfig:list', 'list', 'admin', sysdate(), '', null, 'Tushare接口配置菜单');

-- 二级菜单：下载任务管理
insert into sys_menu values(2002, '下载任务', 2000, 2, 'downloadTask', 'tushare/downloadTask/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadTask:list', 'job', 'admin', sysdate(), '', null, 'Tushare下载任务菜单');

-- 二级菜单：下载日志
insert into sys_menu values(2003, '下载日志', 2000, 3, 'downloadLog', 'tushare/downloadLog/index', '', '', 1, 0, 'C', '0', '0', 'tushare:downloadLog:list', 'log', 'admin', sysdate(), '', null, 'Tushare下载日志菜单');

-- 接口配置按钮
insert into sys_menu values(2100, '接口配置查询', 2001, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2101, '接口配置新增', 2001, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2102, '接口配置修改', 2001, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2103, '接口配置删除', 2001, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2104, '接口配置导出', 2001, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:export', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2105, '接口配置状态修改', 2001, 6, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:apiConfig:changeStatus', '#', 'admin', sysdate(), '', null, '');

-- 下载任务按钮
insert into sys_menu values(2110, '下载任务查询', 2002, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2111, '下载任务新增', 2002, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2112, '下载任务修改', 2002, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2113, '下载任务删除', 2002, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2114, '下载任务状态修改', 2002, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:changeStatus', '#', 'admin', sysdate(), '', null, '');

-- 下载日志按钮
insert into sys_menu values(2120, '下载日志查询', 2003, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2121, '下载日志删除', 2003, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadLog:remove', '#', 'admin', sysdate(), '', null, '');

-- 二级菜单：流程配置管理
insert into sys_menu values(2004, '流程配置', 2000, 1, 'workflowConfig', 'tushare/workflowConfig/index', '', '', 1, 0, 'C', '0', '0', 'tushare:workflowConfig:list', 'tree', 'admin', sysdate(), '', null, 'Tushare流程配置菜单');

-- 二级菜单：流程步骤管理
insert into sys_menu values(2005, '流程步骤', 2000, 5, 'workflowStep', 'tushare/workflowStep/index', '', '', 1, 0, 'C', '1', '0', 'tushare:workflowStep:list', 'tree-table', 'admin', sysdate(), '', null, 'Tushare流程步骤菜单');

-- 流程配置按钮
insert into sys_menu values(2130, '流程配置查询', 2004, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:query', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2131, '流程配置新增', 2004, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2132, '流程配置修改', 2004, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2133, '流程配置删除', 2004, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowConfig:remove', '#', 'admin', sysdate(), '', null, '');

-- 流程步骤按钮
insert into sys_menu values(2140, '流程步骤查询', 2005, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2141, '流程步骤新增', 2005, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2142, '流程步骤修改', 2005, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values(2143, '流程步骤删除', 2005, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:workflowStep:remove', '#', 'admin', sysdate(), '', null, '');

-- 下载任务执行按钮（补充）
insert into sys_menu values(2115, '下载任务执行', 2002, 6, '', '', '', '', 1, 0, 'F', '0', '0', 'tushare:downloadTask:execute', '#', 'admin', sysdate(), '', null, '');

-- ========== 3. 运行表 ==========

-- ----------------------------
-- Tushare下载任务运行表（运行总览） MySQL 版本
-- 与 PostgreSQL 版 tushare_download_run 字段保持一致
-- ----------------------------
DROP TABLE IF EXISTS tushare_download_run;

CREATE TABLE tushare_download_run (
  run_id          BIGINT(20)      NOT NULL AUTO_INCREMENT         COMMENT '运行ID',
  task_id         BIGINT(20)      NOT NULL                        COMMENT '任务ID',
  task_name       VARCHAR(100)    NOT NULL                        COMMENT '任务名称快照',
  status          VARCHAR(20)     NOT NULL                        COMMENT '运行状态（PENDING/RUNNING/SUCCESS/FAILED/CANCELED/TIMEOUT）',
  start_time      DATETIME                                        COMMENT '开始时间',
  end_time        DATETIME                                        COMMENT '结束时间',
  progress        INT(11)         DEFAULT 0                       COMMENT '进度（0-100）',
  total_records   INT(11)         DEFAULT 0                       COMMENT '本次处理总记录数',
  success_records INT(11)         DEFAULT 0                       COMMENT '成功记录数',
  fail_records    INT(11)         DEFAULT 0                       COMMENT '失败记录数',
  error_message   TEXT                                            COMMENT '错误信息',
  create_time     DATETIME        DEFAULT CURRENT_TIMESTAMP       COMMENT '创建时间',
  update_time     DATETIME                                        COMMENT '更新时间',
  PRIMARY KEY (run_id),
  KEY idx_task_id_run (task_id),
  KEY idx_status_run (status),
  KEY idx_start_time_run (start_time),
  KEY idx_end_time_run (end_time)
) ENGINE=InnoDB AUTO_INCREMENT=1 COMMENT='Tushare下载任务运行表（运行总览）';
