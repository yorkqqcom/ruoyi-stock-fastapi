"""
数据库基础模型
"""
from sqlalchemy import create_engine, Column, DateTime, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from config import config

# 创建数据库引擎
engine = create_engine(
    config.DATABASE_URL,
    echo=False,  # 设置为True可以看到SQL语句
    pool_pre_ping=True,  # 连接池预检查
    pool_recycle=3600,   # 连接回收时间
    pool_size=10,        # 连接池大小
    max_overflow=20,     # 最大溢出连接数
    pool_timeout=30,     # 获取连接的超时时间
    connect_args={
        "connect_timeout": 60,      # 连接超时时间
        "read_timeout": 60,         # 读取超时时间
        "write_timeout": 60,        # 写入超时时间
        "autocommit": False,        # 关闭自动提交
    }
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基础模型类
Base = declarative_base()

class BaseModel(Base):
    """基础模型类，包含公共字段"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True, comment='主键ID')
    created_at = Column(DateTime, default=datetime.now, comment='创建时间')
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    
    def to_dict(self):
        """转换为字典"""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
