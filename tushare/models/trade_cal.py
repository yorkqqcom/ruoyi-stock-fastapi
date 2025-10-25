"""
交易日历模型
对应Tushare的trade_cal接口
"""
from sqlalchemy import Column, String, Date, Index
from .base import BaseModel

class TradeCal(BaseModel):
    """交易日历表"""
    __tablename__ = 'trade_cal'
    
    # 主要字段
    exchange = Column(String(10), nullable=False, comment='交易所 SSE上交所 SZSE深交所')
    cal_date = Column(Date, nullable=False, comment='日历日期')
    is_open = Column(String(1), nullable=False, comment='是否交易 0休市 1交易')
    pretrade_date = Column(Date, nullable=True, comment='上一个交易日')
    
    # 创建索引
    __table_args__ = (
        Index('idx_exchange', 'exchange'),
        Index('idx_cal_date', 'cal_date'),
        Index('idx_exchange_date', 'exchange', 'cal_date'),
        Index('idx_is_open', 'is_open'),
    )
    
    def __repr__(self):
        return f"<TradeCal(exchange='{self.exchange}', cal_date='{self.cal_date}', is_open='{self.is_open}')>"
    
    @classmethod
    def get_by_exchange(cls, session, exchange):
        """根据交易所获取交易日历"""
        return session.query(cls).filter(cls.exchange == exchange).order_by(cls.cal_date).all()
    
    @classmethod
    def get_by_date_range(cls, session, start_date, end_date, exchange=None):
        """根据日期范围获取交易日历"""
        query = session.query(cls).filter(cls.cal_date >= start_date, cls.cal_date <= end_date)
        if exchange:
            query = query.filter(cls.exchange == exchange)
        return query.order_by(cls.cal_date).all()
    
    @classmethod
    def get_trading_days(cls, session, start_date, end_date, exchange=None):
        """获取交易日列表"""
        query = session.query(cls).filter(
            cls.cal_date >= start_date, 
            cls.cal_date <= end_date,
            cls.is_open == '1'
        )
        if exchange:
            query = query.filter(cls.exchange == exchange)
        return query.order_by(cls.cal_date).all()
