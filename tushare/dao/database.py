"""
数据库连接管理
"""
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from models.base import Base, SessionLocal, engine
from config import config
from loguru import logger
import pandas as pd

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
    
    def create_tables(self):
        """创建所有表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise
    
    def drop_tables(self):
        """删除所有表"""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("数据库表删除成功")
        except Exception as e:
            logger.error(f"删除数据库表失败: {e}")
            raise
    
    def get_session(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def get_session_with_retry(self, max_retries=3):
        """获取数据库会话，带重试机制"""
        for attempt in range(max_retries):
            try:
                session = SessionLocal()
                # 测试连接是否有效
                session.execute("SELECT 1")
                return session
            except Exception as e:
                logger.warning(f"获取数据库会话失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
    
    def bulk_insert_from_dataframe(self, df, table_name, if_exists='append'):
        """使用pandas批量插入数据"""
        try:
            df.to_sql(
                name=table_name,
                con=self.engine,
                if_exists=if_exists,
                index=False,
                chunksize=config.BATCH_SIZE
            )
            logger.info(f"批量插入数据到 {table_name} 成功，共 {len(df)} 条记录")
        except Exception as e:
            logger.error(f"批量插入数据到 {table_name} 失败: {e}")
            raise
    
    def execute_sql(self, sql, params=None):
        """执行SQL语句"""
        try:
            with self.engine.begin() as conn:
                # 使用text()包装SQL语句
                from sqlalchemy import text
                result = conn.execute(text(sql), params or {})
                return result
        except Exception as e:
            logger.error(f"执行SQL失败: {e}")
            raise

def get_db():
    """获取数据库会话的依赖注入函数"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 创建全局数据库管理器实例
db_manager = DatabaseManager()
