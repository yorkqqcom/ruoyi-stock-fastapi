from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON

from config.database import Base
from config.env import DataBaseConfig


class TushareApiConfig(Base):
    """
    Tushare接口配置表
    """

    __tablename__ = 'tushare_api_config'
    __table_args__ = {'comment': 'Tushare接口配置表'}

    config_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='配置ID')
    api_name = Column(String(100), nullable=False, comment='接口名称')
    api_code = Column(String(100), nullable=False, comment='接口代码（如：stock_basic）')
    api_desc = Column(Text, nullable=True, comment='接口描述')
    api_params = Column(Text, nullable=True, comment='接口参数（JSON格式）')
    data_fields = Column(Text, nullable=True, comment='数据字段（JSON格式，用于指定需要下载的字段）')
    primary_key_fields = Column(Text, nullable=True, comment='主键字段配置（JSON格式，为空则使用默认data_id主键）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')


class TushareDownloadTask(Base):
    """
    Tushare下载任务表
    """

    __tablename__ = 'tushare_download_task'
    __table_args__ = {'comment': 'Tushare下载任务表'}

    task_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    config_id = Column(BigInteger, nullable=True, comment='接口配置ID')
    workflow_id = Column(BigInteger, nullable=True, comment='流程配置ID（如果存在则执行流程，否则执行单个接口）')
    task_type = Column(String(20), nullable=True, server_default='single', comment='任务类型（single:单个接口 workflow:流程配置）')
    cron_expression = Column(String(255), nullable=True, comment='cron执行表达式')
    start_date = Column(String(20), nullable=True, comment='开始日期（YYYYMMDD）')
    end_date = Column(String(20), nullable=True, comment='结束日期（YYYYMMDD）')
    task_params = Column(Text, nullable=True, comment='任务参数（JSON格式，覆盖接口默认参数）')
    save_path = Column(String(500), nullable=True, comment='保存路径')
    save_format = Column(String(20), nullable=True, server_default='csv', comment='保存格式（csv/excel/json）')
    save_to_db = Column(CHAR(1), nullable=True, server_default='0', comment='是否保存到数据库（0否 1是）')
    data_table_name = Column(String(100), nullable=True, comment='数据存储表名（为空则使用默认表tushare_data）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1暂停）')
    last_run_time = Column(DateTime, nullable=True, comment='最后运行时间')
    next_run_time = Column(DateTime, nullable=True, comment='下次运行时间')
    run_count = Column(Integer, nullable=True, server_default='0', comment='运行次数')
    success_count = Column(Integer, nullable=True, server_default='0', comment='成功次数')
    fail_count = Column(Integer, nullable=True, server_default='0', comment='失败次数')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')


class TushareDownloadLog(Base):
    """
    Tushare下载日志表
    """

    __tablename__ = 'tushare_download_log'
    __table_args__ = {'comment': 'Tushare下载日志表'}

    log_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='日志ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    config_id = Column(BigInteger, nullable=False, comment='接口配置ID')
    api_name = Column(String(100), nullable=False, comment='接口名称')
    download_date = Column(String(20), nullable=True, comment='下载日期（YYYYMMDD）')
    record_count = Column(Integer, nullable=True, server_default='0', comment='记录数')
    file_path = Column(String(500), nullable=True, comment='文件路径')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='执行状态（0成功 1失败）')
    error_message = Column(Text, nullable=True, comment='错误信息')
    duration = Column(Integer, nullable=True, comment='执行时长（秒）')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class TushareDownloadRun(Base):
    """
    Tushare下载任务运行表（运行总览）
    """

    __tablename__ = 'tushare_download_run'
    __table_args__ = {'comment': 'Tushare下载任务运行表（运行总览）'}

    run_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='运行ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称快照')
    status = Column(String(20), nullable=False, comment='运行状态（PENDING/RUNNING/SUCCESS/FAILED/CANCELED/TIMEOUT）')
    start_time = Column(DateTime, nullable=True, comment='开始时间')
    end_time = Column(DateTime, nullable=True, comment='结束时间')
    progress = Column(Integer, nullable=True, default=0, comment='进度（0-100）')
    total_records = Column(Integer, nullable=True, default=0, comment='本次处理总记录数')
    success_records = Column(Integer, nullable=True, default=0, comment='成功记录数')
    fail_records = Column(Integer, nullable=True, default=0, comment='失败记录数')
    error_message = Column(Text, nullable=True, comment='错误信息')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class TushareData(Base):
    """
    Tushare数据存储表（通用表）
    """

    __tablename__ = 'tushare_data'
    __table_args__ = {'comment': 'Tushare数据存储表（通用表）'}

    data_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='数据ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    config_id = Column(BigInteger, nullable=False, comment='接口配置ID')
    api_code = Column(String(100), nullable=False, comment='接口代码')
    download_date = Column(String(20), nullable=True, comment='下载日期（YYYYMMDD）')
    # 根据数据库类型选择 JSON 或 JSONB
    if DataBaseConfig.db_type == 'postgresql':
        data_content = Column(JSONB, nullable=True, comment='数据内容（JSONB格式）')
    else:
        data_content = Column(JSON, nullable=True, comment='数据内容（JSON格式）')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class TushareWorkflowConfig(Base):
    """
    Tushare流程配置表
    """

    __tablename__ = 'tushare_workflow_config'
    __table_args__ = {'comment': 'Tushare流程配置表'}

    workflow_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='流程ID')
    workflow_name = Column(String(100), nullable=False, comment='流程名称')
    workflow_desc = Column(Text, nullable=True, comment='流程描述')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')


class TushareWorkflowStep(Base):
    """
    Tushare流程步骤表
    """

    __tablename__ = 'tushare_workflow_step'
    __table_args__ = {'comment': 'Tushare流程步骤表'}

    step_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='步骤ID')
    workflow_id = Column(BigInteger, nullable=False, comment='流程ID')
    step_order = Column(Integer, nullable=False, comment='步骤顺序（从1开始）')
    step_name = Column(String(100), nullable=False, comment='步骤名称')
    config_id = Column(BigInteger, nullable=False, comment='接口配置ID')
    step_params = Column(Text, nullable=True, comment='步骤参数（JSON格式，可从前一步获取数据）')
    condition_expr = Column(Text, nullable=True, comment='执行条件（JSON格式，可选）')
    # 可视化编辑器相关字段
    position_x = Column(Integer, nullable=True, comment='节点X坐标（用于可视化布局）')
    position_y = Column(Integer, nullable=True, comment='节点Y坐标（用于可视化布局）')
    node_type = Column(String(20), nullable=True, server_default='task', comment='节点类型（start/end/task）')
    source_step_ids = Column(Text, nullable=True, comment='前置步骤ID列表（JSON格式，支持多个前置节点）')
    target_step_ids = Column(Text, nullable=True, comment='后置步骤ID列表（JSON格式，支持多个后置节点）')
    # 根据数据库类型选择 JSON 或 JSONB
    if DataBaseConfig.db_type == 'postgresql':
        layout_data = Column(JSONB, nullable=True, comment='完整的布局数据（JSONB格式，存储节点位置、连接线等可视化信息）')
    else:
        layout_data = Column(JSON, nullable=True, comment='完整的布局数据（JSON格式，存储节点位置、连接线等可视化信息）')
    data_table_name = Column(String(100), nullable=True, comment='数据存储表名（为空则使用任务配置的表名或默认表名）')
    loop_mode = Column(CHAR(1), nullable=True, server_default='0', comment='遍历模式（0否 1是，开启后所有变量参数都会遍历）')
    update_mode = Column(CHAR(1), nullable=True, server_default='0', comment='数据更新方式（0仅插入 1忽略重复 2存在则更新 3先删除再插入）')
    unique_key_fields = Column(Text, nullable=True, comment='唯一键字段配置（JSON格式，为空则自动检测）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0正常 1停用）')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')


class TushareProBar(Base):
    """
    Tushare Pro Bar数据表
    """

    __tablename__ = 'tushare_pro_bar'
    __table_args__ = {'comment': 'Tushare Pro Bar数据表'}

    data_id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='数据ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    config_id = Column(BigInteger, nullable=False, comment='配置ID')
    api_code = Column(String(100), nullable=False, comment='接口代码')
    download_date = Column(String(20), nullable=True, comment='下载日期（YYYYMMDD）')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    ts_code = Column(String(500), nullable=True, comment='股票代码')
    trade_date = Column(String(500), nullable=True, comment='交易日期')
    open = Column(Float, nullable=True, comment='开盘价')
    high = Column(Float, nullable=True, comment='最高价')
    low = Column(Float, nullable=True, comment='最低价')
    close = Column(Float, nullable=True, comment='收盘价')
    pre_close = Column(Float, nullable=True, comment='昨收价')
    change = Column(Float, nullable=True, comment='涨跌额')
    pct_chg = Column(Float, nullable=True, comment='涨跌幅')
    vol = Column(Float, nullable=True, comment='成交量')
    amount = Column(Float, nullable=True, comment='成交额')
