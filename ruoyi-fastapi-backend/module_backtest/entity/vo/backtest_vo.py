from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BacktestTaskModel(BaseModel):
    """
    回测任务表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='任务ID')
    task_name: str | None = Field(default=None, description='任务名称')
    scene_code: str | None = Field(default='backtest', description='场景编码（固定为backtest）')
    model_scene_binding_id: int | None = Field(default=None, description='绑定的场景模型ID（可选，用于在线模式）')
    predict_task_id: int | None = Field(default=None, description='预测任务ID（用于离线模式，关联model_train_task）')
    result_id: int | None = Field(default=None, description='训练结果ID（用于在线模式，直接指定模型）')
    symbol_list: str | None = Field(default=None, description='标的列表（ts_code逗号分隔或JSON数组）')
    start_date: str | None = Field(default=None, description='回测开始日期（YYYYMMDD）')
    end_date: str | None = Field(default=None, description='回测结束日期（YYYYMMDD）')
    initial_cash: float | None = Field(default=1000000.0, description='初始资金')
    max_position: float | None = Field(default=1.0, description='最大仓位（0~1，1表示满仓）')
    commission_rate: float | None = Field(default=0.0003, description='手续费率（默认万三）')
    slippage_bp: int | None = Field(default=0, description='滑点（基点，1bp=0.01%）')
    signal_source_type: Literal['predict_table', 'online_model', 'factor_rule'] | None = Field(
        default='predict_table', description='信号来源类型（predict_table/online_model/factor_rule）'
    )
    signal_buy_threshold: float | None = Field(default=0.6, description='买入信号阈值（predict_prob需大于此值）')
    signal_sell_threshold: float | None = Field(default=0.4, description='卖出信号阈值（predict_prob需小于此值）')
    position_mode: Literal['single_stock', 'equal_weight'] | None = Field(
        default='equal_weight', description='持仓模式（single_stock/equal_weight_portfolio）'
    )
    status: Literal['0', '1', '2', '3'] | None = Field(default='0', description='状态（0待执行 1执行中 2成功 3失败）')
    progress: int | None = Field(default=0, description='执行进度（0~100）')
    error_msg: str | None = Field(default=None, description='失败原因')
    remark: str | None = Field(default=None, description='备注信息')
    create_by: str | None = Field(default=None, description='创建者')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_by: str | None = Field(default=None, description='更新者')
    update_time: datetime | None = Field(default=None, description='更新时间')


class BacktestTaskCreateRequestModel(BaseModel):
    """
    创建回测任务请求模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    task_name: str = Field(description='任务名称')
    model_scene_binding_id: Optional[int] = Field(default=None, description='场景绑定ID（在线模式）')
    predict_task_id: Optional[int] = Field(default=None, description='预测任务ID（离线模式）')
    result_id: Optional[int] = Field(default=None, description='训练结果ID（在线模式直接指定）')
    symbol_list: str = Field(description='标的列表（逗号分隔）')
    start_date: str = Field(description='回测开始日期（YYYYMMDD）')
    end_date: str = Field(description='回测结束日期（YYYYMMDD）')
    initial_cash: Optional[float] = Field(default=1000000.0, description='初始资金')
    max_position: Optional[float] = Field(default=1.0, description='最大仓位（0~1）')
    commission_rate: Optional[float] = Field(default=0.0003, description='手续费率')
    slippage_bp: Optional[int] = Field(default=0, description='滑点（基点）')
    signal_source_type: Optional[Literal['predict_table', 'online_model', 'factor_rule']] = Field(
        default='predict_table', description='信号来源类型'
    )
    signal_buy_threshold: Optional[float] = Field(default=0.6, description='买入信号阈值')
    signal_sell_threshold: Optional[float] = Field(default=0.4, description='卖出信号阈值')
    position_mode: Optional[Literal['single_stock', 'equal_weight']] = Field(
        default='equal_weight', description='持仓模式'
    )


class BacktestTaskQueryModel(BaseModel):
    """
    回测任务查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    task_name: Optional[str] = Field(default=None, description='任务名称')
    status: Optional[str] = Field(default=None, description='状态')
    start_date: Optional[str] = Field(default=None, description='开始日期')
    end_date: Optional[str] = Field(default=None, description='结束日期')
    begin_time: Optional[str] = Field(default=None, description='开始时间')
    end_time: Optional[str] = Field(default=None, description='结束时间')


class BacktestTaskPageQueryModel(BacktestTaskQueryModel):
    """
    回测任务分页查询模型
    """

    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class BacktestResultModel(BaseModel):
    """
    回测结果汇总表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='结果ID')
    task_id: int | None = Field(default=None, description='任务ID')
    final_equity: float | None = Field(default=None, description='期末净值')
    total_return: float | None = Field(default=None, description='总收益率')
    annual_return: float | None = Field(default=None, description='年化收益率')
    max_drawdown: float | None = Field(default=None, description='最大回撤')
    volatility: float | None = Field(default=None, description='年化波动率')
    sharpe_ratio: float | None = Field(default=None, description='夏普比率')
    calmar_ratio: float | None = Field(default=None, description='卡玛比率')
    win_rate: float | None = Field(default=None, description='胜率')
    profit_loss_ratio: float | None = Field(default=None, description='盈亏比')
    trade_count: int | None = Field(default=None, description='交易次数')
    equity_curve_json: str | None = Field(default=None, description='净值曲线（JSON格式）')
    create_time: datetime | None = Field(default=None, description='创建时间')
    update_time: datetime | None = Field(default=None, description='更新时间')


class BacktestTradeModel(BaseModel):
    """
    回测交易明细表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='交易ID')
    task_id: int | None = Field(default=None, description='任务ID')
    trade_date: str | None = Field(default=None, description='交易日期（YYYYMMDD）')
    trade_datetime: datetime | None = Field(default=None, description='交易时间')
    ts_code: str | None = Field(default=None, description='股票代码')
    side: str | None = Field(default=None, description='交易方向（buy/sell/close）')
    price: float | None = Field(default=None, description='成交价')
    volume: int | None = Field(default=None, description='成交数量（股）')
    amount: float | None = Field(default=None, description='成交金额')
    fee: float | None = Field(default=None, description='手续费')
    position_after: int | None = Field(default=None, description='操作后持仓（股数）')
    position_value_after: float | None = Field(default=None, description='操作后持仓市值')
    cash_after: float | None = Field(default=None, description='操作后现金')
    equity_after: float | None = Field(default=None, description='操作后总资产')
    create_time: datetime | None = Field(default=None, description='创建时间')


class BacktestTradePageQueryModel(BaseModel):
    """
    回测交易明细分页查询模型
    """

    model_config = ConfigDict(alias_generator=to_camel)

    task_id: int = Field(description='任务ID')
    ts_code: Optional[str] = Field(default=None, description='股票代码')
    start_date: Optional[str] = Field(default=None, description='开始日期')
    end_date: Optional[str] = Field(default=None, description='结束日期')
    page_num: int = Field(default=1, description='当前页码')
    page_size: int = Field(default=10, description='每页记录数')


class BacktestNavModel(BaseModel):
    """
    回测净值日频表对应 pydantic 模型
    """

    model_config = ConfigDict(alias_generator=to_camel, from_attributes=True)

    id: int | None = Field(default=None, description='ID')
    task_id: int | None = Field(default=None, description='任务ID')
    trade_date: str | None = Field(default=None, description='交易日期（YYYYMMDD）')
    nav: float | None = Field(default=None, description='净值')
    cash: float | None = Field(default=None, description='现金')
    position_value: float | None = Field(default=None, description='持仓市值')
    total_equity: float | None = Field(default=None, description='总资产')
    create_time: datetime | None = Field(default=None, description='创建时间')
