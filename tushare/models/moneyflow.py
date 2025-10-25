"""
个股资金流向数据模型
对应Tushare的moneyflow接口
"""
from sqlalchemy import Column, String, Date, DECIMAL, BigInteger, Index
from .base import BaseModel

class MoneyFlow(BaseModel):
    """个股资金流向表"""
    __tablename__ = 'moneyflow'
    
    # 主要字段
    ts_code = Column(String(10), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    
    # 小单数据
    buy_sm_vol = Column(BigInteger, nullable=True, comment='小单买入量(手)')
    buy_sm_amount = Column(DECIMAL(15, 2), nullable=True, comment='小单买入金额(万元)')
    sell_sm_vol = Column(BigInteger, nullable=True, comment='小单卖出量(手)')
    sell_sm_amount = Column(DECIMAL(15, 2), nullable=True, comment='小单卖出金额(万元)')
    
    # 中单数据
    buy_md_vol = Column(BigInteger, nullable=True, comment='中单买入量(手)')
    buy_md_amount = Column(DECIMAL(15, 2), nullable=True, comment='中单买入金额(万元)')
    sell_md_vol = Column(BigInteger, nullable=True, comment='中单卖出量(手)')
    sell_md_amount = Column(DECIMAL(15, 2), nullable=True, comment='中单卖出金额(万元)')
    
    # 大单数据
    buy_lg_vol = Column(BigInteger, nullable=True, comment='大单买入量(手)')
    buy_lg_amount = Column(DECIMAL(15, 2), nullable=True, comment='大单买入金额(万元)')
    sell_lg_vol = Column(BigInteger, nullable=True, comment='大单卖出量(手)')
    sell_lg_amount = Column(DECIMAL(15, 2), nullable=True, comment='大单卖出金额(万元)')
    
    # 特大单数据
    buy_elg_vol = Column(BigInteger, nullable=True, comment='特大单买入量(手)')
    buy_elg_amount = Column(DECIMAL(15, 2), nullable=True, comment='特大单买入金额(万元)')
    sell_elg_vol = Column(BigInteger, nullable=True, comment='特大单卖出量(手)')
    sell_elg_amount = Column(DECIMAL(15, 2), nullable=True, comment='特大单卖出金额(万元)')
    
    # 净流入数据
    net_mf_vol = Column(BigInteger, nullable=True, comment='净流入量(手)')
    net_mf_amount = Column(DECIMAL(15, 2), nullable=True, comment='净流入额(万元)')
    
    # 创建索引
    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_trade_date', 'trade_date'),
        Index('idx_ts_code_trade_date', 'ts_code', 'trade_date'),
        Index('idx_trade_date_ts_code', 'trade_date', 'ts_code'),
        Index('idx_net_mf_amount', 'net_mf_amount'),
        Index('idx_trade_date_net_mf', 'trade_date', 'net_mf_amount'),
    )
    
    def __repr__(self):
        return f"<MoneyFlow(ts_code='{self.ts_code}', trade_date='{self.trade_date}', net_mf_amount='{self.net_mf_amount}')>"
    
    @classmethod
    def get_by_ts_code(cls, session, ts_code, start_date=None, end_date=None):
        """根据股票代码获取资金流向数据"""
        query = session.query(cls).filter(cls.ts_code == ts_code)
        if start_date:
            query = query.filter(cls.trade_date >= start_date)
        if end_date:
            query = query.filter(cls.trade_date <= end_date)
        return query.order_by(cls.trade_date.desc()).all()
    
    @classmethod
    def get_by_trade_date(cls, session, trade_date):
        """根据交易日期获取所有股票资金流向数据"""
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
    
    @classmethod
    def get_top_net_inflow(cls, session, trade_date, limit=20):
        """获取指定日期净流入额最高的股票"""
        return session.query(cls).filter(
            cls.trade_date == trade_date,
            cls.net_mf_amount > 0
        ).order_by(cls.net_mf_amount.desc()).limit(limit).all()
    
    @classmethod
    def get_top_net_outflow(cls, session, trade_date, limit=20):
        """获取指定日期净流出额最高的股票"""
        return session.query(cls).filter(
            cls.trade_date == trade_date,
            cls.net_mf_amount < 0
        ).order_by(cls.net_mf_amount.asc()).limit(limit).all()
