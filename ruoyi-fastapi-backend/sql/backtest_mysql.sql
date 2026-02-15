-- ----------------------------
-- 回测模块（MySQL）：表结构 + 菜单
-- 新环境执行本文件即可；旧库升级见 migrations_mysql.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

drop table if exists backtest_task;
create table backtest_task (
  id                    bigint(20)      not null auto_increment    comment '任务ID',
  task_name             varchar(100)    not null                   comment '任务名称',
  scene_code            varchar(50)     default 'backtest'         comment '场景编码（固定为backtest）',
  model_scene_binding_id bigint(20)                                comment '绑定的场景模型ID（可选，用于在线模式）',
  predict_task_id       bigint(20)                                comment '预测任务ID（用于离线模式，关联model_train_task）',
  result_id             bigint(20)                                comment '训练结果ID（用于在线模式，直接指定模型）',
  symbol_list           text                                       comment '标的列表（ts_code逗号分隔或JSON数组）',
  start_date            varchar(20)    not null                   comment '回测开始日期（YYYYMMDD）',
  end_date              varchar(20)    not null                   comment '回测结束日期（YYYYMMDD）',
  initial_cash          decimal(20,2)  default 1000000.00         comment '初始资金',
  max_position          decimal(5,4)   default 1.0000              comment '最大仓位（0~1，1表示满仓）',
  commission_rate       decimal(8,6)   default 0.0003               comment '手续费率（默认万三）',
  slippage_bp           int(11)        default 0                   comment '滑点（基点，1bp=0.01%）',
  signal_source_type    varchar(20)   default 'predict_table'     comment '信号来源类型（predict_table/online_model/factor_rule）',
  signal_buy_threshold   decimal(5,4)  default 0.6000              comment '买入信号阈值（predict_prob需大于此值）',
  signal_sell_threshold  decimal(5,4)  default 0.4000              comment '卖出信号阈值（predict_prob需小于此值）',
  position_mode          varchar(20)   default 'equal_weight'      comment '持仓模式（single_stock/equal_weight_portfolio）',
  status                char(1)       default '0'                 comment '状态（0待执行 1执行中 2成功 3失败）',
  progress              int(11)       default 0                   comment '执行进度（0~100）',
  error_msg             text                                       comment '失败原因',
  remark                varchar(500)   default ''                  comment '备注信息',
  create_by             varchar(64)    default ''                  comment '创建者',
  create_time           datetime       default current_timestamp   comment '创建时间',
  update_by             varchar(64)    default ''                  comment '更新者',
  update_time           datetime       default current_timestamp on update current_timestamp comment '更新时间',
  primary key (id),
  unique key uk_backtest_task_name (task_name),
  key idx_backtest_task_status (status),
  key idx_backtest_task_time (create_time)
) engine=innodb auto_increment=1 comment = '回测任务表';

drop table if exists backtest_result;
create table backtest_result (
  id                    bigint(20)      not null auto_increment    comment '结果ID',
  task_id               bigint(20)      not null                   comment '任务ID',
  final_equity          decimal(20,2)                              comment '期末净值',
  total_return          decimal(10,6)                              comment '总收益率',
  annual_return         decimal(10,6)                              comment '年化收益率',
  max_drawdown          decimal(10,6)                              comment '最大回撤',
  volatility            decimal(10,6)                              comment '年化波动率',
  sharpe_ratio          decimal(10,6)                              comment '夏普比率',
  calmar_ratio          decimal(10,6)                              comment '卡玛比率',
  win_rate               decimal(10,6)                              comment '胜率',
  profit_loss_ratio     decimal(10,6)                              comment '盈亏比',
  trade_count           int(11)                                    comment '交易次数',
  equity_curve_json     text                                       comment '净值曲线（JSON格式：[{date, nav}, ...]）',
  create_time           datetime       default current_timestamp   comment '创建时间',
  update_time           datetime       default current_timestamp on update current_timestamp comment '更新时间',
  primary key (id),
  unique key uk_backtest_result_task (task_id),
  key idx_backtest_result_time (create_time)
) engine=innodb auto_increment=1 comment = '回测结果汇总表';

drop table if exists backtest_trade;
create table backtest_trade (
  id                    bigint(20)      not null auto_increment    comment '交易ID',
  task_id               bigint(20)      not null                   comment '任务ID',
  trade_date            varchar(20)     not null                   comment '交易日期（YYYYMMDD）',
  trade_datetime        datetime                                   comment '交易时间（精确到秒）',
  ts_code               varchar(50)     not null                   comment '股票代码',
  side                  varchar(10)     not null                   comment '交易方向（buy/sell/close）',
  price                 decimal(10,2)    not null                   comment '成交价',
  volume                int(11)         not null                   comment '成交数量（股）',
  amount                decimal(20,2)    not null                   comment '成交金额',
  fee                   decimal(20,2)    default 0.00               comment '手续费',
  position_after        int(11)                                    comment '操作后持仓（股数）',
  position_value_after  decimal(20,2)                              comment '操作后持仓市值',
  cash_after            decimal(20,2)                              comment '操作后现金',
  equity_after          decimal(20,2)                              comment '操作后总资产',
  create_time           datetime       default current_timestamp   comment '创建时间',
  primary key (id),
  key idx_backtest_trade_task (task_id),
  key idx_backtest_trade_date (trade_date),
  key idx_backtest_trade_code (ts_code),
  key idx_backtest_trade_task_date (task_id, trade_date)
) engine=innodb auto_increment=1 comment = '回测交易明细表';

drop table if exists backtest_nav;
create table backtest_nav (
  id                    bigint(20)      not null auto_increment    comment 'ID',
  task_id               bigint(20)      not null                   comment '任务ID',
  trade_date            varchar(20)     not null                   comment '交易日期（YYYYMMDD）',
  nav                   decimal(20,2)   not null                   comment '净值',
  cash                  decimal(20,2)                              comment '现金',
  position_value        decimal(20,2)                              comment '持仓市值',
  total_equity          decimal(20,2)                              comment '总资产',
  create_time           datetime       default current_timestamp   comment '创建时间',
  primary key (id),
  unique key uk_backtest_nav_task_date (task_id, trade_date),
  key idx_backtest_nav_task (task_id),
  key idx_backtest_nav_date (trade_date)
) engine=innodb auto_increment=1 comment = '回测净值日频表';

-- ========== 2. 菜单 ==========

insert into sys_menu values(4100, '回测管理', 4000, 5, 'backtest', 'backtest/task/index', '', '', 1, 0, 'C', '0', '0', 'backtest:task:list', 'chart', 'admin', current_timestamp, '', null, '回测管理菜单');

-- 回测任务权限（相应调整权限菜单ID）
insert into sys_menu values(4101, '回测任务查询', 4100, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4102, '回测任务新增', 4100, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:create', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4103, '回测任务删除', 4100, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:task:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4104, '回测结果查询', 4100, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:result:query', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4105, '回测交易明细', 4100, 5, '', '', '', '', 1, 0, 'F', '0', '0', 'backtest:trade:list', '#', 'admin', current_timestamp, '', null, '');