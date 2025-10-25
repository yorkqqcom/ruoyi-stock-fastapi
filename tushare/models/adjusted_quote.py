"""
A股复权行情数据模型
对应Tushare的pro_bar接口
"""
from sqlalchemy import Column, String, Date, DECIMAL, BigInteger, Index, Enum
from .base import BaseModel
import enum

class AdjType(enum.Enum):
    """复权类型枚举"""
    NONE = None  # 不复权
    QFQ = 'qfq'  # 前复权
    HFQ = 'hfq'  # 后复权

class AdjustedQuote(BaseModel):
    """A股复权行情表"""
    __tablename__ = 'adjusted_quotes'
    
    # 主要字段
    ts_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    adj_type = Column(String(10), nullable=False, comment='复权类型: None/qfq/hfq')
    open = Column(DECIMAL(10, 2), nullable=True, comment='开盘价')
    high = Column(DECIMAL(10, 2), nullable=True, comment='最高价')
    low = Column(DECIMAL(10, 2), nullable=True, comment='最低价')
    close = Column(DECIMAL(10, 2), nullable=True, comment='收盘价')
    pre_close = Column(DECIMAL(10, 2), nullable=True, comment='昨收价')
    change_amount = Column(DECIMAL(10, 2), nullable=True, comment='涨跌额')
    pct_chg = Column(DECIMAL(8, 4), nullable=True, comment='涨跌幅')
    vol = Column(BigInteger, nullable=True, comment='成交量(手)')
    amount = Column(DECIMAL(15, 2), nullable=True, comment='成交额(千元)')
    
    # 复权相关字段
    adj_factor = Column(DECIMAL(10, 6), nullable=True, comment='复权因子')
    
    # 创建索引
    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_adj_type', 'adj_type'),
        Index('idx_ts_code_trade_date_adj', 'ts_code', 'trade_date', 'adj_type'),
        Index('idx_trade_date_ts_code_adj', 'trade_date', 'ts_code', 'adj_type'),
    )
    
    def __repr__(self):
        return f"<AdjustedQuote(ts_code='{self.ts_code}', trade_date='{self.trade_date}', adj_type='{self.adj_type}', close='{self.close}')>"
    
    @classmethod
    def get_by_ts_code_and_adj(cls, session, ts_code, adj_type, start_date=None, end_date=None):
        """根据股票代码和复权类型获取数据"""
        query = session.query(cls).filter(
            cls.ts_code == ts_code,
            cls.adj_type == adj_type
        )
        if start_date:
            query = query.filter(cls.trade_date >= start_date)
        if end_date:
            query = query.filter(cls.trade_date <= end_date)
        return query.order_by(cls.trade_date.desc()).all()
    
    @classmethod
    def get_by_trade_date_and_adj(cls, session, trade_date, adj_type):
        """根据交易日期和复权类型获取所有股票数据"""
        return session.query(cls).filter(
            cls.trade_date == trade_date,
            cls.adj_type == adj_type
        ).all()
    
    @classmethod
    def get_latest_trade_date(cls, session, adj_type):
        """获取指定复权类型的最新交易日期"""
        result = session.query(cls.trade_date).filter(
            cls.adj_type == adj_type
        ).order_by(cls.trade_date.desc()).first()
        return result[0] if result else None
