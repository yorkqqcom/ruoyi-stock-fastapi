"""
股票基础信息模型
对应Tushare的stock_basic接口
"""
from sqlalchemy import Column, String, Date, Text, Index
from .base import BaseModel

class StockBasic(BaseModel):
    """股票基础信息表"""
    __tablename__ = 'stock_basic'
    
    # 主要字段
    ts_code = Column(String(10), nullable=False, unique=True, comment='TS股票代码')
    symbol = Column(String(10), nullable=False, comment='股票代码')
    name = Column(String(50), nullable=False, comment='股票名称')
    area = Column(String(20), nullable=True, comment='地域')
    industry = Column(String(50), nullable=True, comment='所属行业')
    fullname = Column(String(100), nullable=True, comment='股票全称')
    enname = Column(String(200), nullable=True, comment='英文全称')
    cnspell = Column(String(50), nullable=True, comment='拼音缩写')
    market = Column(String(20), nullable=True, comment='市场类型（主板/创业板/科创板/CDR）')
    exchange = Column(String(10), nullable=True, comment='交易所代码')
    curr_type = Column(String(10), nullable=True, comment='交易货币')
    list_status = Column(String(1), nullable=True, comment='上市状态 L上市 D退市 P暂停上市')
    list_date = Column(Date, nullable=True, comment='上市日期')
    delist_date = Column(Date, nullable=True, comment='退市日期')
    is_hs = Column(String(1), nullable=True, comment='是否沪深港通标的，N否 H沪股通 S深股通')
    act_name = Column(String(100), nullable=True, comment='实控人名称')
    act_ent_type = Column(String(50), nullable=True, comment='实控人企业性质')
    
    # 创建索引
    __table_args__ = (
        Index('idx_ts_code', 'ts_code'),
        Index('idx_symbol', 'symbol'),
        Index('idx_exchange', 'exchange'),
        Index('idx_list_status', 'list_status'),
        Index('idx_market', 'market'),
        Index('idx_industry', 'industry'),
        Index('idx_list_date', 'list_date'),
    )
    
    def __repr__(self):
        return f"<StockBasic(ts_code='{self.ts_code}', name='{self.name}')>"
    
    @classmethod
    def get_by_ts_code(cls, session, ts_code):
        """根据TS代码获取股票信息"""
        return session.query(cls).filter(cls.ts_code == ts_code).first()
    
    @classmethod
    def get_by_symbol(cls, session, symbol):
        """根据股票代码获取股票信息"""
        return session.query(cls).filter(cls.symbol == symbol).first()
    
    @classmethod
    def get_by_exchange(cls, session, exchange):
        """根据交易所获取股票列表"""
        return session.query(cls).filter(cls.exchange == exchange).all()
    
    @classmethod
    def get_active_stocks(cls, session):
        """获取所有正常上市的股票"""
        return session.query(cls).filter(cls.list_status == 'L').all()
