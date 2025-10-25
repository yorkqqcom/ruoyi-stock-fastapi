"""
A股复权因子数据模型
对应Tushare的adj_factor接口
"""
from sqlalchemy import Column, String, Date, DECIMAL, Index
from .base import BaseModel

class AdjFactor(BaseModel):
    """A股复权因子表"""
    __tablename__ = 'adj_factors'
    
    # 主要字段
    ts_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    adj_factor = Column(DECIMAL(12, 6), nullable=False, comment='复权因子')
    
    # 创建索引
    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_ts_code_trade_date', 'ts_code', 'trade_date'),
        Index('idx_trade_date_ts_code', 'trade_date', 'ts_code'),
    )
    
    def __repr__(self):
        return f"<AdjFactor(ts_code='{self.ts_code}', trade_date='{self.trade_date}', adj_factor='{self.adj_factor}')>"
    
    @classmethod
    def get_by_ts_code(cls, session, ts_code, start_date=None, end_date=None):
        """根据股票代码获取复权因子"""
        query = session.query(cls).filter(cls.ts_code == ts_code)
        if start_date:
            query = query.filter(cls.trade_date >= start_date)
        if end_date:
            query = query.filter(cls.trade_date <= end_date)
        return query.order_by(cls.trade_date.desc()).all()
    
    @classmethod
    def get_by_trade_date(cls, session, trade_date):
        """根据交易日期获取所有股票的复权因子"""
        return session.query(cls).filter(cls.trade_date == trade_date).all()
    
    @classmethod
    def get_latest_factor(cls, session, ts_code):
        """获取股票的最新复权因子"""
        return session.query(cls).filter(
            cls.ts_code == ts_code
        ).order_by(cls.trade_date.desc()).first()
