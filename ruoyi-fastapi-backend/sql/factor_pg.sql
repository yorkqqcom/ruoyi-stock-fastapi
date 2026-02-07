-- ----------------------------
-- 因子计算模块（PostgreSQL）：表结构 + 菜单 + 可选示例
-- 新环境执行本文件即可；旧库升级见 migrations_pg.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

drop table if exists factor_definition;
create table factor_definition (
  id                bigint          generated always as identity primary key,
  factor_code       varchar(100)    not null,
  factor_name       varchar(200)    not null,
  category          varchar(50),
  freq              varchar(10)     default 'D',
  window_size       integer,
  calc_type         varchar(20)     default 'PY_EXPR',
  expr              text,
  source_table      varchar(100),
  dependencies      text,
  params            text,
  enable_flag       char(1)         default '0',
  remark            varchar(500)    default '',
  create_by         varchar(64)     default '',
  create_time       timestamp,
  update_by         varchar(64)     default '',
  update_time       timestamp,
  constraint uk_factor_code unique (factor_code)
);
comment on table factor_definition is '因子定义表';

drop table if exists factor_task;
create table factor_task (
  id                bigint          generated always as identity primary key,
  task_name         varchar(100)    not null,
  factor_codes      text,
  symbol_universe   text,
  freq              varchar(10)     default 'D',
  start_date        varchar(20),
  end_date          varchar(20),
  cron_expression   varchar(255),
  run_mode          varchar(20)     default 'increment',
  last_run_time     timestamp,
  next_run_time     timestamp,
  run_count         integer         default 0,
  success_count     integer         default 0,
  fail_count        integer         default 0,
  status            char(1)         default '0',
  params            text,
  remark            varchar(500)    default '',
  create_by         varchar(64)     default '',
  create_time       timestamp,
  update_by         varchar(64)     default '',
  update_time       timestamp,
  constraint uk_factor_task_name unique (task_name)
);
comment on table factor_task is '因子计算任务表';

drop table if exists feature_data;
create table feature_data (
  id                bigint          generated always as identity primary key,
  trade_date        varchar(20)     not null,
  symbol            varchar(50)     not null,
  factor_code       varchar(100)    not null,
  factor_value      numeric(20, 8),
  task_id           bigint,
  calc_date         timestamp       default current_timestamp,
  extra             jsonb
);
comment on table feature_data is '特征数据表（因子计算结果，窄表）';
create index idx_feature_data_main on feature_data (trade_date, factor_code, symbol);
create index idx_feature_data_task on feature_data (task_id);
create index idx_feature_data_calc_date on feature_data (calc_date);

drop table if exists factor_calc_log;
create table factor_calc_log (
  id                bigint          generated always as identity primary key,
  task_id           bigint          not null,
  task_name         varchar(100)    not null,
  factor_codes      text,
  symbol_universe   text,
  start_date        varchar(20),
  end_date          varchar(20),
  status            char(1)         default '0',
  record_count      integer         default 0,
  duration          integer,
  error_message     text,
  create_time       timestamp       default current_timestamp
);
comment on table factor_calc_log is '因子计算日志表';
create index idx_factor_calc_log_task on factor_calc_log (task_id);
create index idx_factor_calc_log_time on factor_calc_log (create_time);

-- ========== 2. 菜单 ==========

insert into sys_menu values(3000, '因子管理', 0, 2, 'factor', null, '', '', 1, 0, 'M', '0', '0', '', 'build', 'admin', current_timestamp, '', null, '因子管理目录');
insert into sys_menu values(3001, '因子定义', 3000, 1, 'definition', 'factor/definition/index', '', '', 1, 0, 'C', '0', '0', 'factor:definition:list', 'list', 'admin', current_timestamp, '', null, '因子定义菜单');
insert into sys_menu values(3002, '因子任务', 3000, 2, 'task', 'factor/task/index', '', '', 1, 0, 'C', '0', '0', 'factor:task:list', 'job', 'admin', current_timestamp, '', null, '因子任务菜单');
insert into sys_menu values(3100, '因子定义查询', 3001, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3101, '因子定义新增', 3001, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3102, '因子定义修改', 3001, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3103, '因子定义删除', 3001, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3110, '因子任务查询', 3002, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3111, '因子任务新增', 3002, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:add', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3112, '因子任务修改', 3002, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:edit', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3113, '因子任务删除', 3002, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3114, '因子任务状态修改', 3002, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:changeStatus', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3115, '因子任务执行', 3002, 6, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:execute', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3004, '因子计算日志', 3000, 4, 'calcLog', 'factor/calcLog/index', '', '', 1, 0, 'C', '0', '0', 'factor:calcLog:list', 'log', 'admin', current_timestamp, '', null, '因子计算日志菜单');
insert into sys_menu values(3121, '因子计算日志查询', 3004, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:calcLog:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(3116, '因子计算日志查看', 3002, 7, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:calcLog:list', '#', 'admin', current_timestamp, '', null, '');

-- ========== 3. 可选：示例因子任务（按需取消注释并调整日期） ==========


INSERT INTO factor_definition (factor_code,factor_name,category,freq,window_size,calc_type,expr,source_table,dependencies,params,enable_flag,remark,create_by,create_time,update_by,update_time) VALUES
	 ('technical_ema_10','技术指标_technical_ema_10','TECHNICAL','D',20,'PY_EXPR','df.sort_values(["ts_code", "trade_date"]).groupby("ts_code")["close"].transform(lambda x: x.ewm(span=10, adjust=False).mean())','tushare_pro_bar',NULL,NULL,'0','auto generated from features by script at 2026-01-27 23:40:44','',NULL,'admin','2026-01-28 15:28:18.293391'),
	 ('technical_ema_5','技术指标_technical_ema_5','TECHNICAL','D',20,'PY_EXPR','df.sort_values(["ts_code", "trade_date"]).groupby("ts_code")["close"].transform(lambda x: x.ewm(span=5, adjust=False).mean())','tushare_pro_bar',NULL,NULL,'0','auto generated from features by script at 2026-01-27 23:40:44','',NULL,'admin','2026-01-28 15:28:24.599363'),
	 ('technical_sma_10','技术指标_technical_sma_10','TECHNICAL','D',20,'PY_EXPR','df.sort_values(["ts_code", "trade_date"]).groupby("ts_code")["close"].transform(lambda x: x.rolling(window=10, min_periods=1).mean())','tushare_pro_bar',NULL,NULL,'0','auto generated from features by script at 2026-01-27 23:40:44','',NULL,'admin','2026-01-28 15:28:29.723699'),
	 ('technical_sma_5','技术指标_technical_sma_5','TECHNICAL','D',20,'PY_EXPR','df.sort_values(["ts_code", "trade_date"]).groupby("ts_code")["close"].transform(lambda x: x.rolling(window=5, min_periods=1).mean())','tushare_pro_bar',NULL,NULL,'0','auto generated from features by script at 2026-01-27 23:40:44','',NULL,'admin','2026-01-28 15:28:36.508886');


INSERT INTO factor_task (
    task_name, factor_codes, symbol_universe, freq, start_date, end_date,
    cron_expression, run_mode, status, remark, create_by, create_time
) VALUES (
    '技术指标因子计算任务示例',
    'technical_sma_5,technical_ema_5,technical_sma_10,technical_ema_10',
    NULL, 'D', '20240101', '20250128', NULL, 'increment', '0',
    '测试4个技术指标因子：SMA5/EMA5/SMA10/EMA10', 'admin', CURRENT_TIMESTAMP
);