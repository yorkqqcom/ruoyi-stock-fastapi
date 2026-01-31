-- ----------------------------
-- 模型训练模块（MySQL）：表结构 + 菜单 + 示例数据
-- 新环境执行本文件即可；旧库升级见 migrations_mysql.sql
-- ----------------------------

-- ========== 1. 表结构 ==========

drop table if exists model_train_task;
create table model_train_task (
  id                bigint(20)      not null auto_increment    comment '任务ID',
  task_name         varchar(100)    not null                   comment '任务名称',
  factor_codes      text                                       comment '因子代码列表（JSON或逗号分隔）',
  symbol_universe   text                                       comment '标的范围定义（全部/指数成分/自定义列表，JSON格式）',
  start_date        varchar(20)                                comment '训练开始日期（YYYYMMDD）',
  end_date          varchar(20)                                comment '训练结束日期（YYYYMMDD）',
  model_params      text                                       comment '模型参数（JSON格式，如n_estimators, max_depth等）',
  train_test_split  decimal(5,2)   default 0.8                 comment '训练集比例（默认0.8）',
  status            char(1)        default '0'                 comment '状态（0待训练 1训练中 2训练完成 3训练失败）',
  last_run_time     datetime                                   comment '最后运行时间',
  run_count         int(11)       default 0                   comment '运行次数',
  success_count     int(11)       default 0                   comment '成功次数',
  fail_count        int(11)       default 0                   comment '失败次数',
  remark            varchar(500)   default ''                  comment '备注信息',
  create_by         varchar(64)    default ''                  comment '创建者',
  create_time       datetime                                   comment '创建时间',
  update_by         varchar(64)    default ''                  comment '更新者',
  update_time       datetime                                   comment '更新时间',
  primary key (id),
  unique key uk_model_train_task_name (task_name)
) engine=innodb auto_increment=1 comment = '模型训练任务表';

drop table if exists model_train_result;
create table model_train_result (
  id                bigint(20)     not null auto_increment     comment '结果ID',
  task_id           bigint(20)     not null                    comment '任务ID',
  version           int(11)        not null default 1           comment '模型版本号（同一任务内从1递增）',
  task_name         varchar(100)   not null                    comment '任务名称快照',
  model_file_path   varchar(500)                               comment '模型文件路径',
  accuracy          decimal(10,6)                              comment '准确率',
  precision_score   decimal(10,6)                             comment '精确率',
  recall_score      decimal(10,6)                              comment '召回率',
  f1_score          decimal(10,6)                             comment 'F1分数',
  confusion_matrix  text                                       comment '混淆矩阵（JSON格式）',
  feature_importance text                                      comment '特征重要性（JSON格式）',
  train_samples     int(11)                                    comment '训练样本数',
  test_samples      int(11)                                    comment '测试样本数',
  train_duration    int(11)                                    comment '训练时长（秒）',
  status            char(1)       default '0'                  comment '状态（0成功 1失败）',
  error_message     text                                       comment '错误信息',
  create_time       datetime       default current_timestamp   comment '创建时间',
  primary key (id),
  key idx_model_train_result_task (task_id),
  key idx_model_train_result_time (create_time),
  key idx_model_train_result_task_version (task_id, version)
) engine=innodb auto_increment=1 comment = '模型训练结果表';

drop table if exists model_predict_result;
create table model_predict_result (
  id                bigint(20)     not null auto_increment     comment '预测ID',
  result_id         bigint(20)     not null                    comment '训练结果ID',
  ts_code           varchar(50)    not null                    comment '股票代码',
  trade_date        varchar(20)    not null                    comment '交易日期（YYYYMMDD）',
  predict_label     int(11)                                    comment '预测标签（1=涨，0=跌）',
  predict_prob      decimal(10,6)                              comment '预测概率（涨的概率）',
  actual_label      int(11)                                    comment '实际标签（用于回测，1=涨，0=跌）',
  is_correct        char(1)                                    comment '预测是否正确（1=正确，0=错误）',
  create_time       datetime       default current_timestamp   comment '创建时间',
  primary key (id),
  key idx_model_predict_result (result_id, ts_code, trade_date),
  key idx_model_predict_date (trade_date)
) engine=innodb auto_increment=1 comment = '模型预测结果表';

drop table if exists model_scene_binding;
create table model_scene_binding (
  id                bigint(20)     not null auto_increment     comment '绑定ID',
  task_id           bigint(20)     not null                    comment '训练任务ID',
  scene_code        varchar(50)    not null                    comment '场景编码（如live、backtest、default等）',
  result_id         bigint(20)     not null                    comment '绑定的训练结果ID',
  is_active         char(1)       default '1'                  comment '是否当前生效（1是 0否）',
  remark            varchar(500)   default ''                  comment '备注信息',
  create_time       datetime       default current_timestamp   comment '创建时间',
  update_time       datetime       default current_timestamp on update current_timestamp comment '更新时间',
  primary key (id),
  key idx_model_scene_binding_task_scene (task_id, scene_code),
  key idx_model_scene_binding_result (result_id)
) engine=innodb auto_increment=1 comment = '模型场景绑定表';

-- ========== 2. 菜单 ==========

insert into sys_menu values('4000', '模型管理', '0', '7', 'model', null, '', '', 1, 0, 'M', '0', '0', '', 'tree-table', 'admin', sysdate(), '', null, '模型管理目录');
insert into sys_menu values('3999', '因子配置文件', '4000', '0', 'config', 'factor/model/config/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:config:list', 'list', 'admin', sysdate(), '', null, '因子配置文件菜单');
insert into sys_menu values('4001', '模型训练任务', '4000', '1', 'task', 'factor/model/task/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:task:list', 'tree', 'admin', sysdate(), '', null, '模型训练任务菜单');
insert into sys_menu values('4002', '模型训练结果', '4000', '2', 'result', 'factor/model/result/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:result:list', 'chart', 'admin', sysdate(), '', null, '模型训练结果菜单');
insert into sys_menu values('4003', '模型预测结果', '4000', '3', 'predict', 'factor/model/predict/index', '', '', 1, 0, 'C', '0', '0', 'factor:model:predict:list', 'eye', 'admin', sysdate(), '', null, '模型预测结果菜单');
insert into sys_menu values('4009', '因子配置文件查询', '3999', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:config:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4010', '模型训练任务查询', '4001', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4011', '模型训练任务新增', '4001', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:train', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4012', '模型训练任务执行', '4001', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:execute', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4013', '模型训练任务删除', '4001', '4', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:task:remove', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4020', '模型训练结果查询', '4002', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:result:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4021', '模型训练结果详情', '4002', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:result:detail', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4022', '模型场景绑定', '4002', '3', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:scene:bind', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4030', '模型预测结果查询', '4003', '1', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:predict:list', '#', 'admin', sysdate(), '', null, '');
insert into sys_menu values('4031', '模型预测执行', '4003', '2', '', '', '', '', 1, 0, 'F', '0', '0', 'factor:model:predict', '#', 'admin', sysdate(), '', null, '');

-- ========== 3. 示例数据（按需调整日期后执行） ==========

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '技术指标模型训练示例',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    NULL, '20230101', '20231231',
    '{"n_estimators": 100, "max_depth": 10, "min_samples_split": 2, "random_state": 42}',
    0.8, '0', '使用EMA和SMA技术指标训练随机森林模型，预测未来1天的涨跌方向',
    'admin', NOW(), 'admin', NOW()
);

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '指定股票技术指标模型训练',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    '["000001.SZ","000002.SZ","600000.SH","600036.SH"]', '20230101', '20231231',
    '{"n_estimators": 200, "max_depth": 15, "min_samples_split": 5, "min_samples_leaf": 2, "random_state": 42}',
    0.75, '0', '针对特定股票池训练模型，使用更多树和更深的深度',
    'admin', NOW(), 'admin', NOW()
);

INSERT INTO model_train_task (
    task_name, factor_codes, symbol_universe, start_date, end_date, model_params,
    train_test_split, status, remark, create_by, create_time, update_by, update_time
) VALUES (
    '多因子组合模型训练',
    'technical_ema_10,technical_ema_5,technical_sma_10,technical_sma_5',
    NULL, '20220101', '20231231',
    '{"n_estimators": 150, "max_depth": 12, "min_samples_split": 3, "max_features": "sqrt", "random_state": 42}',
    0.8, '0', '使用多因子组合，增加特征随机性以提高模型泛化能力',
    'admin', NOW(), 'admin', NOW()
);
