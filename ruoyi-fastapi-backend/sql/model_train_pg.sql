-- ----------------------------
-- 模型训练模块（PostgreSQL）：表结构 + 菜单 + 示例数据
-- 新环境执行本文件即可；旧库升级见 migrations_pg.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

drop table if exists model_train_task;
create table model_train_task (
  id                bigint          generated always as identity primary key,
  task_name         varchar(100)    not null,
  factor_codes      text,
  symbol_universe   text,
  start_date        varchar(20),
  end_date          varchar(20),
  model_params      text,
  train_test_split  numeric(5,2)    default 0.8,
  status            char(1)         default '0',
  last_run_time     timestamp,
  run_count         integer         default 0,
  success_count     integer         default 0,
  fail_count        integer         default 0,
  remark            varchar(500)    default '',
  create_by         varchar(64)     default '',
  create_time       timestamp,
  update_by         varchar(64)     default '',
  update_time       timestamp,
  constraint uk_model_train_task_name unique (task_name)
);
comment on table model_train_task is '模型训练任务表';

drop table if exists model_train_result;
create table model_train_result (
  id                bigint          generated always as identity primary key,
  task_id           bigint          not null,
  version           integer         default 1,
  task_name         varchar(100)    not null,
  model_file_path   varchar(500),
  accuracy          numeric(10,6),
  precision_score   numeric(10,6),
  recall_score      numeric(10,6),
  f1_score          numeric(10,6),
  confusion_matrix  text,
  feature_importance text,
  train_samples     integer,
  test_samples      integer,
  train_duration    integer,
  status            char(1)         default '0',
  error_message     text,
  create_time       timestamp       default current_timestamp
);
comment on table model_train_result is '模型训练结果表';
create index idx_model_train_result_task on model_train_result (task_id);
create index idx_model_train_result_time on model_train_result (create_time);
create index idx_model_train_result_task_version on model_train_result (task_id, version);

drop table if exists model_predict_result;
create table model_predict_result (
  id                bigint          generated always as identity primary key,
  result_id         bigint          not null,
  ts_code           varchar(50)     not null,
  trade_date        varchar(20)     not null,
  predict_label     integer,
  predict_prob      numeric(10,6),
  actual_label      integer,
  is_correct        char(1),
  create_time       timestamp       default current_timestamp
);
comment on table model_predict_result is '模型预测结果表';
create index idx_model_predict_result on model_predict_result (result_id, ts_code, trade_date);
create index idx_model_predict_date on model_predict_result (trade_date);

drop table if exists model_scene_binding;
create table model_scene_binding (
  id                bigint          generated always as identity primary key,
  task_id           bigint          not null,
  scene_code        varchar(50)     not null,
  result_id         bigint          not null,
  is_active         char(1)         default '1',
  remark            varchar(500)    default '',
  create_time       timestamp       default current_timestamp,
  update_time       timestamp       default current_timestamp
);
comment on table model_scene_binding is '模型场景绑定表';
create index idx_model_scene_binding_task_scene on model_scene_binding (task_id, scene_code);
create index idx_model_scene_binding_result on model_scene_binding (result_id);

-- ========== 2. 菜单 ==========

insert into sys_menu values(4000, '模型管理', 0, 3, 'model', null, '', '', 1, 0, 'M', '0', '0', '', 'tree-table', 'admin', current_timestamp, '', null, '模型管理目录');
insert into sys_menu values(3999, '因子配置文件', 4000, 0, 'modelconfig', 'factor/model/config/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:config:list', 'list', 'admin', current_timestamp, '', null, '因子配置文件菜单');
insert into sys_menu values(4001, '模型训练任务', 4000, 1, 'modeltask', 'factor/model/task/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:task:list', 'tree', 'admin', current_timestamp, '', null, '模型训练任务菜单');
insert into sys_menu values(4002, '模型训练结果', 4000, 2, 'result', 'factor/model/result/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:result:list', 'chart', 'admin', current_timestamp, '', null, '模型训练结果菜单');
insert into sys_menu values(4003, '模型预测结果', 4000, 3, 'predict', 'factor/model/predict/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:predict:list', 'eye', 'admin', current_timestamp, '', null, '模型预测结果菜单');
insert into sys_menu values(4009, '因子配置文件查询', 3999, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:config:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4010, '模型训练任务查询', 4001, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4011, '模型训练任务新增', 4001, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:train', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4012, '模型训练任务执行', 4001, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:execute', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4013, '模型训练任务删除', 4001, 4, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:remove', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4020, '模型训练结果查询', 4002, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:result:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4021, '模型训练结果详情', 4002, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:result:detail', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4022, '模型场景绑定', 4002, 3, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:scene:bind', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4030, '模型预测结果查询', 4003, 1, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:predict:list', '#', 'admin', current_timestamp, '', null, '');
insert into sys_menu values(4031, '模型预测执行', 4003, 2, '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:predict', '#', 'admin', current_timestamp, '', null, '');

-- ========== 3. 示例数据（按需调整日期后执行） ==========

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '技术指标模型训练示例',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    NULL, '20250101', '20251231',
    '{"n_estimators": 100, "max_depth": 10, "min_samples_split": 2, "random_state": 42}',
    0.8, '0', '使用EMA和SMA技术指标训练随机森林模型，预测未来1天的涨跌方向',
    'admin', CURRENT_TIMESTAMP, 'admin', CURRENT_TIMESTAMP
);

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '指定股票技术指标模型训练',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    '["000001.SZ","000002.SZ","600000.SH","600036.SH"]', '20250101', '20251231',
    '{"n_estimators": 200, "max_depth": 15, "min_samples_split": 5, "min_samples_leaf": 2, "random_state": 42}',
    0.75, '0', '针对特定股票池训练模型，使用更多树和更深的深度',
    'admin', CURRENT_TIMESTAMP, 'admin', CURRENT_TIMESTAMP
);

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '多因子组合模型训练',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    NULL, '20250101', '20251231',
    '{"n_estimators": 150, "max_depth": 12, "min_samples_split": 3, "max_features": "sqrt", "random_state": 42}',
    0.8, '0', '使用多因子组合，增加特征随机性以提高模型泛化能力',
    'admin', CURRENT_TIMESTAMP, 'admin', CURRENT_TIMESTAMP
);
