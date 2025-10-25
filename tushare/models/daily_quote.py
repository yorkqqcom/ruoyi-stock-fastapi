"""
A股日线行情数据模型
对应Tushare的daily接口
"""
from sqlalchemy import Column, String, Date, DECIMAL, BigInteger, Index
from .base import BaseModel

class DailyQuote(BaseModel):
    """A股日线行情表"""
    __tablename__ = 'daily_quotes'
    
    # 主要字段
    ts_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    open = Column(DECIMAL(10, 2), nullable=True, comment='开盘价')
    high = Column(DECIMAL(10, 2), nullable=True, comment='最高价')
    low = Column(DECIMAL(10, 2), nullable=True, comment='最低价')
    close = Column(DECIMAL(10, 2), nullable=True, comment='收盘价')
    pre_close = Column(DECIMAL(10, 2), nullable=True, comment='昨收价')
    change_amount = Column(DECIMAL(10, 2), nullable=True, comment='涨跌额')
    pct_chg = Column(DECIMAL(8, 4), nullable=True, comment='涨跌幅')
    vol = Column(BigInteger, nullable=True, comment='成交量(手)')
    amount = Column(DECIMAL(15, 2), nullable=True, comment='成交额(千元)')
    
    # 创建索引
    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_ts_code_trade_date', 'ts_code', 'trade_date'),
        Index('idx_trade_date_ts_code', 'trade_date', 'ts_code'),
    )
    
    def __repr__(self):
        return f"<DailyQuote(ts_code='{self.ts_code}', trade_date='{self.trade_date}', close='{self.close}')>"
    
    @classmethod
    def get_by_ts_code(cls, session, ts_code, start_date=None, end_date=None):
        """根据股票代码获取日线数据"""
        query = session.query(cls).filter(cls.ts_code == ts_code)
        if start_date:
            query = query.filter(cls.trade_date >= start_date)
        if end_date:
            query = query.filter(cls.trade_date <= end_date)
        return query.order_by(cls.trade_date.desc()).all()
    
    @classmethod
    def get_by_trade_date(cls, session, trade_date):
        """根据交易日期获取所有股票数据"""
        return session.query(cls).filter(cls.trade_date == trade_date).all()
    
    @classmethod
    def get_latest_trade_date(cls, session):
        """获取最新的交易日期"""
        result = session.query(cls.trade_date).order_by(cls.trade_date.desc()).first()
        return result[0] if result else None
    
    @classmethod
    def get_date_range(cls, session):
        """获取数据日期范围"""
        min_date = session.query(cls.trade_date).order_by(cls.trade_date.asc()).first()
        max_date = session.query(cls.trade_date).order_by(cls.trade_date.desc()).first()
        return (min_date[0] if min_date else None, max_date[0] if max_date else None)
