from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_validation_decorator import NotBlank, Size


class FactorDefinitionModel(BaseModel):
    """
    因子定义表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    factor_code: str | None = Field(default=None, description='因子代码')
    factor_name: str | None = Field(default=None, description='因子名称')
    category: str | None = Field(default=None, description='因子类别（技术面/财务面/情绪面等）')
    freq: str | None = Field(default='D', description='频率（D/W/M等）')
    window: int | None = Field(default=None, description='滚动窗口长度')
    calc_type: Literal['PY_EXPR', 'SQL_EXPR', 'CUSTOM_PY'] | None = Field(
        default='PY_EXPR', description='计算类型（PY_EXPR/SQL_EXPR/CUSTOM_PY）'
    )
    expr: str | None = Field(default=None, description='因子计算表达式或函数路径')
    source_table: str | None = Field(default=None, description='数据来源表标识（如daily_price）')
    dependencies: str | None = Field(default=None, description='依赖因子列表（JSON格式）')
    params: str | None = Field(default=None, description='附加参数（JSON格式）')
    enable_flag: Literal['0', '1'] | None = Field(default='0', description='是否启用（0启用 1停用）')
    remark: str | None = Field(default=None, description='备注信息')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')

    @NotBlank(field_name='factor_code', message='因子代码不能为空')
    @Size(field_name='factor_code', min_length=1, max_length=100, message='因子代码长度不能超过100个字符')
    def get_factor_code(self) -> str | None:
        return self.factor_code

    @NotBlank(field_name='factor_name', message='因子名称不能为空')
    @Size(field_name='factor_name', min_length=1, max_length=200, message='因子名称长度不能超过200个字符')
    def get_factor_name(self) -> str | None:
        return self.factor_name

    def validate_fields(self) -> None:
        self.get_factor_code()
        self.get_factor_name()


class FactorDefinitionQueryModel(FactorDefinitionModel):
    """
    因子定义查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class FactorDefinitionPageQueryModel(FactorDefinitionQueryModel):
    """
    因子定义分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditFactorDefinitionModel(FactorDefinitionModel):
    """
    编辑因子定义模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteFactorDefinitionModel(BaseModel):
    """
    删除因子定义模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    factor_ids: str = Field(description='需要删除的因子ID')


class FactorTaskModel(BaseModel):
    """
    因子计算任务表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    factor_codes: str | None = Field(default=None, description='因子代码列表（JSON或逗号分隔）')
    symbol_universe: str | None = Field(default=None, description='标的范围定义（JSON格式）')
    freq: str | None = Field(default='D', description='计算频率（D/W/M等）')
    start_date: str | None = Field(default=None, description='开始日期（YYYYMMDD）')
    end_date: str | None = Field(default=None, description='结束日期（YYYYMMDD）')
    cron_expression: str | None = Field(default=None, description='cron执行表达式')
    run_mode: Literal['full', 'increment'] | None = Field(
        default='increment', description='运行模式（full/increment）'
    )
    last_run_time: datetime | None = Field(default=None, description='最后运行时间')
    next_run_time: datetime | None = Field(default=None, description='下次运行时间')
    run_count: int | None = Field(default=None, description='运行次数')
    success_count: int | None = Field(default=None, description='成功次数')
    fail_count: int | None = Field(default=None, description='失败次数')
    status: Literal['0', '1'] | None = Field(default='0', description='状态（0正常 1暂停）')
    params: str | None = Field(default=None, description='任务级附加参数（JSON格式）')
    remark: str | None = Field(default=None, description='备注信息')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')

    @NotBlank(field_name='task_name', message='任务名称不能为空')
    @Size(field_name='task_name', min_length=1, max_length=100, message='任务名称长度不能超过100个字符')
    def get_task_name(self) -> str | None:
        return self.task_name

    def validate_fields(self) -> None:
        self.get_task_name()


class FactorTaskQueryModel(FactorTaskModel):
    """
    因子任务查询模型
    """

    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class FactorTaskPageQueryModel(FactorTaskQueryModel):
    """
    因子任务分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditFactorTaskModel(FactorTaskModel):
    """
    编辑因子任务模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteFactorTaskModel(BaseModel):
    """
    删除因子任务模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_ids: str = Field(description='需要删除的任务ID')


class FactorValueModel(BaseModel):
    """
    因子结果模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='主键ID')
    trade_date: str | None = Field(default=None, description='交易日期（YYYYMMDD）')
    symbol: str | None = Field(default=None, description='证券代码')
    factor_code: str | None = Field(default=None, description='因子代码')
    factor_value: float | None = Field(default=None, description='因子值')
    task_id: int | None = Field(default=None, description='任务ID')
    calc_date: datetime | None = Field(default=None, description='计算时间')
    extra: dict | None = Field(default=None, description='附加信息（JSON）')


class FactorValueQueryModel(BaseModel):
    """
    因子结果查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    symbol: str | None = Field(default=None, description='证券代码')
    factor_codes: str | None = Field(default=None, description='因子代码列表（逗号分隔）')
    start_date: str | None = Field(default=None, description='开始日期（YYYYMMDD）')
    end_date: str | None = Field(default=None, description='结束日期（YYYYMMDD）')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class FactorCalcLogModel(BaseModel):
    """
    因子计算日志模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='日志ID')
    task_id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    factor_codes: str | None = Field(default=None, description='本次计算的因子代码列表')
    symbol_universe: str | None = Field(default=None, description='本次计算的标的范围')
    start_date: str | None = Field(default=None, description='本次计算开始日期')
    end_date: str | None = Field(default=None, description='本次计算结束日期')
    status: Literal['0', '1'] | None = Field(default='0', description='执行状态（0成功 1失败）')
    record_count: int | None = Field(default=None, description='计算记录数')
    duration: int | None = Field(default=None, description='执行时长（秒）')
    error_message: str | None = Field(default=None, description='错误信息')
    create_time: datetime | None = Field(default=None, description='创建时间')


class FactorCalcLogQueryModel(BaseModel):
    """
    因子计算日志查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    status: Literal['0', '1'] | None = Field(default=None, description='执行状态（0成功 1失败）')
    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class FactorCalcLogPageQueryModel(FactorCalcLogQueryModel):
    """
    因子计算日志分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


# ==================== 模型训练相关模型 ====================


class ModelTrainTaskModel(BaseModel):
    """
    模型训练任务表对应 pydantic 模型
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        from_attributes=True,
        populate_by_name=True,  # 允许用字段名 task_name 或别名 taskName 构造，避免 controller 传 task_name 被忽略
    )

    id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    factor_codes: str | None = Field(default=None, description='因子代码列表（JSON或逗号分隔）')
    symbol_universe: str | None = Field(default=None, description='标的范围定义（JSON格式）')
    start_date: str | None = Field(default=None, description='训练开始日期（YYYYMMDD）')
    end_date: str | None = Field(default=None, description='训练结束日期（YYYYMMDD）')
    model_params: str | None = Field(default=None, description='模型参数（JSON格式）')
    train_test_split: float | None = Field(default=0.8, description='训练集比例（默认0.8）')
    status: Literal['0', '1', '2', '3'] | None = Field(
        default='0', description='状态（0待训练 1训练中 2训练完成 3训练失败）'
    )
    last_run_time: datetime | None = Field(default=None, description='最后运行时间')
    run_count: int | None = Field(default=0, description='运行次数')
    success_count: int | None = Field(default=0, description='成功次数')
    fail_count: int | None = Field(default=0, description='失败次数')
    remark: str | None = Field(default=None, description='备注信息')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')

    @NotBlank(field_name='task_name', message='任务名称不能为空')
    @Size(field_name='task_name', min_length=1, max_length=100, message='任务名称长度不能超过100个字符')
    def get_task_name(self) -> str | None:
        return self.task_name

    def validate_fields(self) -> None:
        self.get_task_name()


class ModelTrainTaskQueryModel(BaseModel):
    """
    模型训练任务查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_name: str | None = Field(default=None, description='任务名称')
    status: Literal['0', '1', '2', '3'] | None = Field(default=None, description='状态')
    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class ModelTrainTaskPageQueryModel(ModelTrainTaskQueryModel):
    """
    模型训练任务分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class EditModelTrainTaskModel(ModelTrainTaskModel):
    """
    编辑模型训练任务模型
    """

    type: str | None = Field(default=None, description='操作类型')


class DeleteModelTrainTaskModel(BaseModel):
    """
    删除模型训练任务模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_ids: str = Field(description='需要删除的任务ID')


class ModelTrainResultModel(BaseModel):
    """
    模型训练结果表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='结果ID')
    task_id: int | None = Field(default=None, description='任务ID')
    version: int | None = Field(default=None, description='模型版本号（同一任务内从1递增）')
    task_name: str | None = Field(default=None, description='任务名称快照')
    model_file_path: str | None = Field(default=None, description='模型文件路径')
    accuracy: float | None = Field(default=None, description='准确率')
    precision_score: float | None = Field(default=None, description='精确率')
    recall_score: float | None = Field(default=None, description='召回率')
    f1_score: float | None = Field(default=None, description='F1分数')
    confusion_matrix: str | None = Field(default=None, description='混淆矩阵（JSON格式）')
    feature_importance: str | None = Field(default=None, description='特征重要性（JSON格式）')
    train_samples: int | None = Field(default=None, description='训练样本数')
    test_samples: int | None = Field(default=None, description='测试样本数')
    train_duration: int | None = Field(default=None, description='训练时长（秒）')
    status: Literal['0', '1'] | None = Field(default='0', description='状态（0成功 1失败）')
    error_message: str | None = Field(default=None, description='错误信息')
    create_time: datetime | None = Field(default=None, description='创建时间')


class ModelTrainResultQueryModel(BaseModel):
    """
    模型训练结果查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    status: Literal['0', '1'] | None = Field(default=None, description='状态')
    begin_time: str | None = Field(default=None, description='开始时间')
    end_time: str | None = Field(default=None, description='结束时间')


class ModelTrainResultPageQueryModel(ModelTrainResultQueryModel):
    """
    模型训练结果分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class ModelPredictResultModel(BaseModel):
    """
    模型预测结果表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='预测ID')
    result_id: int | None = Field(default=None, description='训练结果ID')
    ts_code: str | None = Field(default=None, description='股票代码')
    trade_date: str | None = Field(default=None, description='交易日期（YYYYMMDD）')
    predict_label: int | None = Field(default=None, description='预测标签（1=涨，0=跌）')
    predict_prob: float | None = Field(default=None, description='预测概率（涨的概率）')
    actual_label: int | None = Field(default=None, description='实际标签（用于回测，1=涨，0=跌）')
    is_correct: Literal['0', '1'] | None = Field(default=None, description='预测是否正确（1=正确，0=错误）')
    create_time: datetime | None = Field(default=None, description='创建时间')


class ModelPredictResultQueryModel(BaseModel):
    """
    模型预测结果查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    result_id: int | None = Field(default=None, description='训练结果ID')
    ts_code: str | None = Field(default=None, description='股票代码')
    start_date: str | None = Field(default=None, description='开始日期（YYYYMMDD）')
    end_date: str | None = Field(default=None, description='结束日期（YYYYMMDD）')


class ModelPredictResultPageQueryModel(ModelPredictResultQueryModel):
    """
    模型预测结果分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class ModelTrainRequestModel(BaseModel):
    """
    模型训练请求模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True, populate_by_name=True)

    task_name: str = Field(description='任务名称')
    factor_codes: str = Field(description='因子代码列表（JSON或逗号分隔）')
    symbol_universe: str | None = Field(default=None, description='标的范围定义（JSON格式）')
    start_date: str = Field(description='训练开始日期（YYYYMMDD）')
    end_date: str = Field(description='训练结束日期（YYYYMMDD）')
    model_params: str | None = Field(
        default='{"n_estimators": 100, "max_depth": 10, "min_samples_split": 2}',
        description='模型参数（JSON格式）',
    )
    train_test_split: float | None = Field(default=0.8, description='训练集比例（默认0.8）')


class ModelPredictRequestModel(BaseModel):
    """
    模型预测请求模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    # 二选一：要么直接指定训练结果ID，要么通过 (taskId + sceneCode) 使用场景绑定的模型
    result_id: int | None = Field(default=None, description='训练结果ID（可选，与taskId/sceneCode二选一）')
    task_id: int | None = Field(default=None, description='训练任务ID（与sceneCode配合使用）')
    scene_code: str | None = Field(default=None, description='预测场景编码（如live、backtest、default等）')
    ts_codes: str | None = Field(default=None, description='股票代码列表（逗号分隔，为空则预测所有）')
    trade_date: str = Field(description='交易日期（YYYYMMDD）')


class ModelSceneBindRequestModel(BaseModel):
    """
    模型场景绑定请求模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    task_id: int = Field(description='训练任务ID')
    scene_code: str = Field(description='场景编码（如live、backtest、default等）')
    result_id: int = Field(description='要绑定的训练结果ID')

