-- ----------------------------
-- 因子计算模块（MySQL）：表结构 + 菜单 + 可选示例
-- 新环境执行本文件即可；旧库升级见 migrations_mysql.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

-- 1、因子定义表
drop table if exists factor_definition;
create table factor_definition (
  id                bigint(20)      not null auto_increment    comment '主键ID',
  factor_code       varchar(100)    not null                   comment '因子代码',
  factor_name       varchar(200)    not null                   comment '因子名称',
  category          varchar(50)                                 comment '因子类别（技术面/财务面/情绪面等）',
  freq              varchar(10)     default 'D'                comment '频率（D/W/M等）',
  window_size       int(11)                                    comment '滚动窗口长度',
  calc_type         varchar(20)     default 'PY_EXPR'          comment '计算类型（PY_EXPR/SQL_EXPR/CUSTOM_PY）',
  expr              text                                       comment '因子计算表达式或函数路径',
  source_table      varchar(100)                               comment '数据来源表标识（如daily_price）',
  dependencies      text                                       comment '依赖因子列表（JSON格式）',
  params            text                                       comment '附加参数（JSON格式）',
  enable_flag       char(1)         default '0'                comment '是否启用（0启用 1停用）',
  remark            varchar(500)    default ''                 comment '备注信息',
  create_by         varchar(64)     default ''                 comment '创建者',
  create_time       datetime                                   comment '创建时间',
  update_by         varchar(64)     default ''                 comment '更新者',
  update_time       datetime                                   comment '更新时间',
  primary key (id),
  unique key uk_factor_code (factor_code)
) engine=innodb auto_increment=1 comment = '因子定义表';

-- 2、因子计算任务表
drop table if exists factor_task;
create table factor_task (
  id                bigint(20)      not null auto_increment    comment '任务ID',
  task_name         varchar(100)    not null                   comment '任务名称',
  factor_codes      text                                       comment '因子代码列表（JSON或逗号分隔）',
  symbol_universe   text                                       comment '标的范围定义（全部/指数成分/自定义列表，JSON格式）',
  freq              varchar(10)     default 'D'                comment '计算频率（D/W/M等）',
  start_date        varchar(20)                                comment '开始日期（YYYYMMDD）',
  end_date          varchar(20)                                comment '结束日期（YYYYMMDD）',
  cron_expression   varchar(255)                               comment 'cron执行表达式（为空表示仅手动触发）',
  run_mode          varchar(20)     default 'increment'        comment '运行模式（full/increment）',
  last_run_time     datetime                                   comment '最后运行时间',
  next_run_time     datetime                                   comment '下次运行时间',
  run_count         int(11)         default 0                  comment '运行次数',
  success_count     int(11)         default 0                  comment '成功次数',
  fail_count        int(11)         default 0                  comment '失败次数',
  status            char(1)         default '0'                comment '状态（0正常 1暂停）',
  params            text                                       comment '任务级附加参数（JSON格式）',
  remark            varchar(500)    default ''                 comment '备注信息',
  create_by         varchar(64)     default ''                 comment '创建者',
  create_time       datetime                                   comment '创建时间',
  update_by         varchar(64)     default ''                 comment '更新者',
  update_time       datetime                                   comment '更新时间',
  primary key (id),
  unique key uk_factor_task_name (task_name)
) engine=innodb auto_increment=1 comment = '因子计算任务表';

-- 3、特征数据表（因子计算结果，窄表）
drop table if exists feature_data;
create table feature_data (
  id                bigint(20)      not null auto_increment    comment '主键ID',
  trade_date        varchar(20)     not null                   comment '交易日期（YYYYMMDD）',
  symbol            varchar(50)     not null                   comment '证券代码',
  factor_code       varchar(100)    not null                   comment '因子代码',
  factor_value      decimal(20,8)                               comment '因子值',
  task_id           bigint(20)                                  comment '任务ID',
  calc_date         datetime        default current_timestamp  comment '计算时间',
  extra             json                                       comment '附加信息（JSON格式）',
  primary key (id),
  key idx_feature_data_main (trade_date, factor_code, symbol),
  key idx_feature_data_task (task_id),
  key idx_feature_data_calc_date (calc_date)
) engine=innodb auto_increment=1 comment = '特征数据表（因子计算结果，窄表）';

-- 4、因子计算日志表
drop table if exists factor_calc_log;
create table factor_calc_log (
  id                bigint(20)      not null auto_increment    comment '日志ID',
  task_id           bigint(20)      not null                   comment '任务ID',
  task_name         varchar(100)    not null                   comment '任务名称',
  factor_codes      text                                       comment '本次计算的因子代码列表',
  symbol_universe   text                                       comment '本次计算的标的范围',
  start_date        varchar(20)                                comment '本次计算开始日期',
  end_date          varchar(20)                                comment '本次计算结束日期',
  status            char(1)         default '0'                comment '执行状态（0成功 1失败）',
  record_count      int(11)         default 0                  comment '计算记录数',
  duration          int(11)                                    comment '执行时长（秒）',
  error_message     text                                       comment '错误信息',
  create_time       datetime        default current_timestamp comment '创建时间',
  primary key (id),
  key idx_factor_calc_log_task (task_id),
  key idx_factor_calc_log_time (create_time)
) engine=innodb auto_increment=1 comment = '因子计算日志表';

-- ========== 2. 菜单 ==========

insert into sys_menu values('3000', '因子管理', '0', '6', 'factor', null, '', '', 1, 0, 'M', '0', '0', '', 'analysis', 'admin', sysdate(), '', null, '因子管理目录');
insert into sys_menu values('3001', '因子定义', '3000', '1', 'definition', 'factor/definition/index', '', '', 1, 0, 'C', '0', '0', 'factor:definition:list', 'list', 'admin', sysdate(), '', null, '因子定义菜单');
insert into sys_menu values('3002', '因子任务', '3000', '2', 'task', 'factor/task/index', '', '', 1, 0, 'C', '0', '0', 'factor:task:list', 'job', 'admin', sysdate(), '', null, '因子任务菜单');
insert into sys_menu values('3003', '因子结果', '3000', '3', 'value', 'factor/value/index', '', '', 1, 0, 'C', '0', '0', 'factor:value:list', 'trend', 'admin', sysdate(), '', null, '因子结果查询菜单');
insert into sys_menu values('3100', '因子定义查询', '3001', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3101', '因子定义新增', '3001', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3102', '因子定义修改', '3001', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3103', '因子定义删除', '3001', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:definition:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3110', '因子任务查询', '3002', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3111', '因子任务新增', '3002', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:add', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3112', '因子任务修改', '3002', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:edit', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3113', '因子任务删除', '3002', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3114', '因子任务状态修改', '3002', '5', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:changeStatus', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3115', '因子任务执行', '3002', '6', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:task:execute', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3120', '因子结果查询', '3003', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:value:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3004', '因子计算日志', '3000', '4', 'calcLog', 'factor/calcLog/index', '', '', 1, 0, 'C', '0', '0', 'factor:calcLog:list', 'log', 'admin', sysdate(), '', null, '因子计算日志菜单');
insert into sys_menu values('3121', '因子计算日志查询', '3004', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:calcLog:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('3116', '因子计算日志查看', '3002', '7', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:calcLog:list', '#', 'admin', sysdate(), '', null, '');

-- ========== 3. 可选：示例因子任务（按需取消注释并调整日期） ==========
-- 请根据 tushare_pro_bar 表实际数据范围调整 start_date、end_date
/*
INSERT INTO factor_task (
    task_name, factor_codes, symbol_universe, freq, start_date, end_date,
    cron_expression, run_mode, status, remark, create_by, create_time
) VALUES (
    '技术指标因子计算任务示例',
    'technical_sma_5,technical_ema_5,technical_sma_10,technical_ema_10',
    NULL, 'D', '20240101', '20250128', NULL, 'increment', '0',
    '测试4个技术指标因子：SMA5/EMA5/SMA10/EMA10', 'admin', NOW()
);
*/
