-- ----------------------------
-- 回测模块（PostgreSQL）：表结构 + 菜单
-- 新环境执行本文件即可；旧库升级见 migrations_pg.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

drop table if exists backtest_task;
create table backtest_task (
  id                    bigint          generated always as identity primary key,
  task_name             varchar(100)    not null,
  scene_code            varchar(50)     default 'backtest',
  model_scene_binding_id bigint,
  predict_task_id       bigint,
  result_id             bigint,
  symbol_list           text,
  start_date            varchar(20)     not null,
  end_date              varchar(20)     not null,
  initial_cash          numeric(20,2)  default 1000000.00,
  max_position          numeric(5,4)    default 1.0000,
  commission_rate       numeric(8,6)    default 0.0003,
  slippage_bp           integer         default 0,
  signal_source_type    varchar(20)     default 'predict_table',
  signal_buy_threshold  numeric(5,4)    default 0.6000,
  signal_sell_threshold numeric(5,4)     default 0.4000,
  position_mode         varchar(20)     default 'equal_weight',
  status                char(1)         default '0',
  progress              integer          default 0,
  error_msg             text,
  remark                varchar(500)    default '',
  create_by             varchar(64)     default '',
  create_time           timestamp        default current_timestamp,
  update_by             varchar(64)     default '',
  update_time           timestamp        default current_timestamp
);
comment on table backtest_task is '回测任务表';
create index idx_backtest_task_status on backtest_task (status);
create index idx_backtest_task_time on backtest_task (create_time);

drop table if exists backtest_result;
create table backtest_result (
  id                    bigint          generated always as identity primary key,
  task_id               bigint          not null,
  final_equity          numeric(20,2),
  total_return          numeric(10,6),
  annual_return         numeric(10,6),
  max_drawdown          numeric(10,6),
  volatility            numeric(10,6),
  sharpe_ratio          numeric(10,6),
  calmar_ratio          numeric(10,6),
  win_rate               numeric(10,6),
  profit_loss_ratio     numeric(10,6),
  trade_count           integer,
  equity_curve_json     text,
  create_time           timestamp        default current_timestamp,
  update_time           timestamp        default current_timestamp,
  constraint uk_backtest_result_task unique (task_id)
);
comment on table backtest_result is '回测结果汇总表';
create index idx_backtest_result_time on backtest_result (create_time);

drop table if exists backtest_trade;
create table backtest_trade (
  id                    bigint          generated always as identity primary key,
  task_id               bigint          not null,
  trade_date            varchar(20)     not null,
  trade_datetime        timestamp,
  ts_code               varchar(50)     not null,
  side                  varchar(10)     not null,
  price                 numeric(10,2)   not null,
  volume                integer         not null,
  amount                numeric(20,2)    not null,
  fee                   numeric(20,2)   default 0.00,
  position_after        integer,
  position_value_after  numeric(20,2),
  cash_after            numeric(20,2),
  equity_after          numeric(20,2),
  create_time           timestamp        default current_timestamp
);
comment on table backtest_trade is '回测交易明细表';
create index idx_backtest_trade_task on backtest_trade (task_id);
create index idx_backtest_trade_date on backtest_trade (trade_date);
create index idx_backtest_trade_code on backtest_trade (ts_code);
create index idx_backtest_trade_task_date on backtest_trade (task_id, trade_date);

drop table if exists backtest_nav;
create table backtest_nav (
  id                    bigint          generated always as identity primary key,
  task_id               bigint          not null,
  trade_date            varchar(20)     not null,
  nav                   numeric(20,2)   not null,
  cash                  numeric(20,2),
  position_value        numeric(20,2),
  total_equity          numeric(20,2),
  create_time           timestamp        default current_timestamp,
  constraint uk_backtest_nav_task_date unique (task_id, trade_date)
);
comment on table backtest_nav is '回测净值日频表';
create index idx_backtest_nav_task on backtest_nav (task_id);
create index idx_backtest_nav_date on backtest_nav (trade_date);

-- ========== 2. 菜单 ==========

insert into sys_menu values(4100, '回测管理', 4000, 5, 'backtest', 'backtest/task/index', '', '', 1, 0, 'C', '0', '0', 'backtest:task:list', 'chart', 'admin', current_timestamp, '', null, '回测管理菜单');

-- 回测任务权限（相应调整权限菜单ID）
insert into sys_menu values(4101, '回测任务查询', 4100, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4102, '回测任务新增', 4100, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:create', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4103, '回测任务删除', 4100, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4104, '回测结果查询', 4100, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:result:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4105, '回测交易明细', 4100, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:trade:list', '#', 'admin', current_timestamp, '', null, '');