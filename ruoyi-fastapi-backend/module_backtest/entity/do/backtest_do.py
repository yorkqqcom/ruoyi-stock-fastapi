from datetime import datetime

from sqlalchemy import CHAR, BigInteger, Column, DateTime, Integer, Numeric, String, Text

from config.database import Base


class BacktestTask(Base):
    """
    回测任务表
    """

    __tablename__ = 'backtest_task'
    __table_args__ = {'comment': '回测任务表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='任务ID')
    task_name = Column(String(100), nullable=False, comment='任务名称')
    scene_code = Column(String(50), nullable=True, server_default='backtest', comment='场景编码（固定为backtest）')
    model_scene_binding_id = Column(BigInteger, nullable=True, comment='绑定的场景模型ID（可选，用于在线模式）')
    predict_task_id = Column(BigInteger, nullable=True, comment='预测任务ID（用于离线模式，关联model_train_task）')
    result_id = Column(BigInteger, nullable=True, comment='训练结果ID（用于在线模式，直接指定模型）')
    symbol_list = Column(Text, nullable=True, comment='标的列表（ts_code逗号分隔或JSON数组）')
    start_date = Column(String(20), nullable=False, comment='回测开始日期（YYYYMMDD）')
    end_date = Column(String(20), nullable=False, comment='回测结束日期（YYYYMMDD）')
    initial_cash = Column(Numeric(20, 2), nullable=True, server_default='1000000.00', comment='初始资金')
    max_position = Column(Numeric(5, 4), nullable=True, server_default='1.0000', comment='最大仓位（0~1，1表示满仓）')
    commission_rate = Column(Numeric(8, 6), nullable=True, server_default='0.0003', comment='手续费率（默认万三）')
    slippage_bp = Column(Integer, nullable=True, server_default='0', comment='滑点（基点，1bp=0.01%）')
    signal_source_type = Column(String(20), nullable=True, server_default='predict_table', comment='信号来源类型（predict_table/online_model/factor_rule）')
    signal_buy_threshold = Column(Numeric(5, 4), nullable=True, server_default='0.6000', comment='买入信号阈值（predict_prob需大于此值）')
    signal_sell_threshold = Column(Numeric(5, 4), nullable=True, server_default='0.4000', comment='卖出信号阈值（predict_prob需小于此值）')
    position_mode = Column(String(20), nullable=True, server_default='equal_weight', comment='持仓模式（single_stock/equal_weight_portfolio）')
    status = Column(CHAR(1), nullable=True, server_default='0', comment='状态（0待执行 1执行中 2成功 3失败）')
    progress = Column(Integer, nullable=True, server_default='0', comment='执行进度（0~100）')
    error_msg = Column(Text, nullable=True, comment='失败原因')
    remark = Column(String(500), nullable=True, server_default="''", comment='备注信息')
    create_by = Column(String(64), nullable=True, server_default="''", comment='创建者')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_by = Column(String(64), nullable=True, server_default="''", comment='更新者')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class BacktestResult(Base):
    """
    回测结果汇总表
    """

    __tablename__ = 'backtest_result'
    __table_args__ = {'comment': '回测结果汇总表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='结果ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    final_equity = Column(Numeric(20, 2), nullable=True, comment='期末净值')
    total_return = Column(Numeric(10, 6), nullable=True, comment='总收益率')
    annual_return = Column(Numeric(10, 6), nullable=True, comment='年化收益率')
    max_drawdown = Column(Numeric(10, 6), nullable=True, comment='最大回撤')
    volatility = Column(Numeric(10, 6), nullable=True, comment='年化波动率')
    sharpe_ratio = Column(Numeric(10, 6), nullable=True, comment='夏普比率')
    calmar_ratio = Column(Numeric(10, 6), nullable=True, comment='卡玛比率')
    win_rate = Column(Numeric(10, 6), nullable=True, comment='胜率')
    profit_loss_ratio = Column(Numeric(10, 6), nullable=True, comment='盈亏比')
    trade_count = Column(Integer, nullable=True, comment='交易次数')
    equity_curve_json = Column(Text, nullable=True, comment='净值曲线（JSON格式：[{date, nav}, ...]）')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
    update_time = Column(DateTime, nullable=True, default=datetime.now(), comment='更新时间')


class BacktestTrade(Base):
    """
    回测交易明细表
    """

    __tablename__ = 'backtest_trade'
    __table_args__ = {'comment': '回测交易明细表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='交易ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    trade_date = Column(String(20), nullable=False, comment='交易日期（YYYYMMDD）')
    trade_datetime = Column(DateTime, nullable=True, comment='交易时间（精确到秒）')
    ts_code = Column(String(50), nullable=False, comment='股票代码')
    side = Column(String(10), nullable=False, comment='交易方向（buy/sell/close）')
    price = Column(Numeric(10, 2), nullable=False, comment='成交价')
    volume = Column(Integer, nullable=False, comment='成交数量（股）')
    amount = Column(Numeric(20, 2), nullable=False, comment='成交金额')
    fee = Column(Numeric(20, 2), nullable=True, server_default='0.00', comment='手续费')
    position_after = Column(Integer, nullable=True, comment='操作后持仓（股数）')
    position_value_after = Column(Numeric(20, 2), nullable=True, comment='操作后持仓市值')
    cash_after = Column(Numeric(20, 2), nullable=True, comment='操作后现金')
    equity_after = Column(Numeric(20, 2), nullable=True, comment='操作后总资产')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')


class BacktestNav(Base):
    """
    回测净值日频表
    """

    __tablename__ = 'backtest_nav'
    __table_args__ = {'comment': '回测净值日频表'}

    id = Column(BigInteger, primary_key=True, nullable=False, autoincrement=True, comment='ID')
    task_id = Column(BigInteger, nullable=False, comment='任务ID')
    trade_date = Column(String(20), nullable=False, comment='交易日期（YYYYMMDD）')
    nav = Column(Numeric(20, 2), nullable=False, comment='净值')
    cash = Column(Numeric(20, 2), nullable=True, comment='现金')
    position_value = Column(Numeric(20, 2), nullable=True, comment='持仓市值')
    total_equity = Column(Numeric(20, 2), nullable=True, comment='总资产')
    create_time = Column(DateTime, nullable=True, default=datetime.now(), comment='创建时间')
