from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, Float, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from config.database import Base
from config.env import DataBaseConfig


class FactorDefinition(Base):
    """
    因子定义表
    """

    __tablename__ = 'factor_definition'
    __table_args__ = {'comment': '因子定义表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    factor_code = Column(String(100), nullable=False, comment='因子代码')
    factor_name = Column(String(200), nullable=False, comment='因子名称')
    category = Column(String(50), nullable=True, comment='因子类别（技术面/财务面/情绪面等）')
    freq = Column(String(10), nullable=False, server_default='D', comment='频率（D/W/M等）')
    window = Column('window_size', Integer, nullable=True, comment='滚动窗口长度')
    calc_type = Column(String(20), nullable=False, server_default='PY_EXPR', comment='计算类型（PY_EXPR/SQL_EXPR/CUSTOM_PY）')
    expr = Column(Text, nullable=True, comment='因子计算表达式或函数路径')
    source_table = Column(String(100), nullable=True, comment='数据来源表标识（如daily_price）')
    dependencies = Column(Text, nullable=True, comment='依赖因子列表（JSON格式）')
    params = Column(Text, nullable=True, comment='附加参数（JSON格式）')
    enable_flag = Column(CHAR(1), nullable=True, server_default='0', comment='是否启用（0启用 1停用）')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class FactorTask(Base):
    """
    因子计算任务表
    """

    __tablename__ = 'factor_task'
    __table_args__ = {'comment': '因子计算任务表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    factor_codes = Column(Text, nullable=False, comment='因子代码列表（JSON或逗号分隔）')
    symbol_universe = Column(Text, nullable=True, comment='标的范围定义（全部/指数成分/自定义列表，JSON格式）')
    freq = Column(String(10), nullable=False, server_default='D', comment='计算频率（D/W/M等）')
    start_date = Column(String(20), nullable=True, comment='开始日期（YYYYMMDD）')
    end_date = Column(String(20), nullable=True, comment='结束日期（YYYYMMDD）')
    cron_expression = Column(String(255), nullable=True, comment='cron执行表达式（为空表示仅手动触发）')
    run_mode = Column(String(20), nullable=True, server_default='increment', comment='运行模式（full/increment）')
    last_run_time = Column(DateTime, nullable=True, comment='最后运行时间')
    next_run_time = Column(DateTime, nullable=True, comment='下次运行时间')
    run_count = Column(Integer, nullable=True, server_default='0', comment='运行次数')
    success_count = Column(Integer, nullable=True, server_default='0', comment='成功次数')
    fail_count = Column(Integer, nullable=True, server_default='0', comment='失败次数')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1暂停）')
    params = Column(Text, nullable=True, comment='任务级附加参数（JSON格式）')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class FactorValue(Base):
    """
    因子值表（特征/因子数据，窄表）
    """

    __tablename__ = 'factor_value'
    __table_args__ = {'comment': '因子值表（特征/因子数据，窄表）'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='主键ID')
    trade_date = Column(String(20), nullable=False, comment='交易日期（YYYYMMDD）')
    symbol = Column(String(50), nullable=False, comment='证券代码')
    factor_code = Column(String(100), nullable=False, comment='因子代码')
    factor_value = Column(Numeric(20, 8), nullable=True, comment='因子值')
    task_id = Column(BigInteger, nullable=True, comment='任务ID')
    calc_date = Column(DateTime, nullable=True, default=datetime.now(), comment='计算时间')
    extra = None
    # 根据数据库类型选择 JSON 或 JSONB
    if DataBaseConfig.db_type == 'postgresql':
        extra = Column(JSONB, nullable=True, comment='附加信息（JSONB格式）')
    else:
        extra = Column(JSON, nullable=True, comment='附加信息（JSON格式）')


class FactorCalcLog(Base):
    """
    因子计算日志表
    """

    __tablename__ = 'factor_calc_log'
    __table_args__ = {'comment': '因子计算日志表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='日志ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    factor_codes = Column(Text, nullable=True, comment='本次计算的因子代码列表')
    symbol_universe = Column(Text, nullable=True, comment='本次计算的标的范围')
    start_date = Column(String(20), nullable=True, comment='本次计算开始日期')
    end_date = Column(String(20), nullable=True, comment='本次计算结束日期')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='执行状态（0成功 1失败）')
    record_count = Column(Integer, nullable=True, server_default='0', comment='计算记录数')
    duration = Column(Integer, nullable=True, comment='执行时长（秒）')
    error_message = Column(Text, nullable=True, comment='错误信息')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class ModelTrainTask(Base):
    """
    模型训练任务表
    """

    __tablename__ = 'model_train_task'
    __table_args__ = {'comment': '模型训练任务表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    factor_codes = Column(Text, nullable=True, comment='因子代码列表（JSON或逗号分隔）')
    symbol_universe = Column(Text, nullable=True, comment='标的范围定义（全部/指数成分/自定义列表，JSON格式）')
    start_date = Column(String(20), nullable=True, comment='训练开始日期（YYYYMMDD）')
    end_date = Column(String(20), nullable=True, comment='训练结束日期（YYYYMMDD）')
    model_params = Column(Text, nullable=True, comment='模型参数（JSON格式，如n_estimators, max_depth等）')
    train_test_split = Column(Numeric(5, 2), nullable=True, server_default='0.8', comment='训练集比例（默认0.8）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0待训练 1训练中 2训练完成 3训练失败）')
    last_run_time = Column(DateTime, nullable=True, comment='最后运行时间')
    run_count = Column(Integer, nullable=True, server_default='0', comment='运行次数')
    success_count = Column(Integer, nullable=True, server_default='0', comment='成功次数')
    fail_count = Column(Integer, nullable=True, server_default='0', comment='失败次数')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class ModelTrainResult(Base):
    """
    模型训练结果表
    """

    __tablename__ = 'model_train_result'
    __table_args__ = {'comment': '模型训练结果表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='结果ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    version = Column(Integer, nullable=False, server_default='1', comment='模型版本号（同一任务内从1递增）')
    task_name = Column(String(100), nullable=False, comment='任务名称快照')
    model_file_path = Column(String(500), nullable=True, comment='模型文件路径')
    accuracy = Column(Numeric(10, 6), nullable=True, comment='准确率')
    precision_score = Column(Numeric(10, 6), nullable=True, comment='精确率')
    recall_score = Column(Numeric(10, 6), nullable=True, comment='召回率')
    f1_score = Column(Numeric(10, 6), nullable=True, comment='F1分数')
    confusion_matrix = Column(Text, nullable=True, comment='混淆矩阵（JSON格式）')
    feature_importance = Column(Text, nullable=True, comment='特征重要性（JSON格式）')
    train_samples = Column(Integer, nullable=True, comment='训练样本数')
    test_samples = Column(Integer, nullable=True, comment='测试样本数')
    train_duration = Column(Integer, nullable=True, comment='训练时长（秒）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0成功 1失败）')
    error_message = Column(Text, nullable=True, comment='错误信息')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class ModelPredictResult(Base):
    """
    模型预测结果表
    """

    __tablename__ = 'model_predict_result'
    __table_args__ = {'comment': '模型预测结果表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='预测ID')
    result_id = Column(BigInteger, nullable=False, comment='训练结果ID')
    ts_code = Column(String(50), nullable=False, comment='股票代码')
    trade_date = Column(String(20), nullable=False, comment='交易日期（YYYYMMDD）')
    predict_label = Column(Integer, nullable=True, comment='预测标签（1=涨，0=跌）')
    predict_prob = Column(Numeric(10, 6), nullable=True, comment='预测概率（涨的概率）')
    actual_label = Column(Integer, nullable=True, comment='实际标签（用于回测，1=涨，0=跌）')
    is_correct = Column(CHAR(1), nullable=True, comment='预测是否正确（1=正确，0=错误）')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class ModelSceneBinding(Base):
    """
    模型场景绑定表
    """

    __tablename__ = 'model_scene_binding'
    __table_args__ = {'comment': '模型场景绑定表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='绑定ID')
    task_id = Column(BigInteger, nullable=False, comment='训练任务ID')
    scene_code = Column(String(50), nullable=False, comment='场景编码（如live、backtest、default等）')
    result_id = Column(BigInteger, nullable=False, comment='绑定的训练结果ID')
    is_active = Column(CHAR(1), nullable=True, server_default='1', comment='是否当前生效（1是 0否）')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')

