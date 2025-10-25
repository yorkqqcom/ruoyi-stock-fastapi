"""
股票基础信息数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.stock_basic import StockBasic
from typing import List, Optional, Dict, Any
from loguru import logger
import pandas as pd
from datetime import datetime

class StockBasicDAO:
    """股票基础信息数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, stock_data: Dict[str, Any]) -> StockBasic:
        """创建股票基础信息记录"""
        try:
            stock = StockBasic(**stock_data)
            self.session.add(stock)
            self.session.commit()
            logger.info(f"创建股票基础信息成功: {stock.ts_code}")
            return stock
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建股票基础信息失败: {e}")
            raise
    
    def bulk_create(self, stocks_data: List[Dict[str, Any]]) -> int:
        """批量创建股票基础信息记录"""
        try:
            stocks = [StockBasic(**data) for data in stocks_data]
            self.session.add_all(stocks)
            self.session.commit()
            logger.info(f"批量创建股票基础信息成功，共 {len(stocks)} 条记录")
            return len(stocks)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建股票基础信息失败: {e}")
            raise
    
    def get_by_ts_code(self, ts_code: str) -> Optional[StockBasic]:
        """根据TS代码获取股票信息"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.ts_code == ts_code).first()
        except Exception as e:
            logger.error(f"根据TS代码获取股票信息失败: {e}")
            raise
    
    def get_by_symbol(self, symbol: str) -> Optional[StockBasic]:
        """根据股票代码获取股票信息"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.symbol == symbol).first()
        except Exception as e:
            logger.error(f"根据股票代码获取股票信息失败: {e}")
            raise
    
    def get_all(self, limit: Optional[int] = None) -> List[StockBasic]:
        """获取所有股票基础信息"""
        try:
            query = self.session.query(StockBasic)
            if limit:
                query = query.limit(limit)
            return query.all()
        except Exception as e:
            logger.error(f"获取所有股票基础信息失败: {e}")
            raise
    
    def get_by_exchange(self, exchange: str) -> List[StockBasic]:
        """根据交易所获取股票列表"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.exchange == exchange).all()
        except Exception as e:
            logger.error(f"根据交易所获取股票列表失败: {e}")
            raise
    
    def get_active_stocks(self) -> List[StockBasic]:
        """获取所有正常上市的股票"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.list_status == 'L').all()
        except Exception as e:
            logger.error(f"获取正常上市股票失败: {e}")
            raise
    
    def get_by_market(self, market: str) -> List[StockBasic]:
        """根据市场类型获取股票列表"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.market == market).all()
        except Exception as e:
            logger.error(f"根据市场类型获取股票列表失败: {e}")
            raise
    
    def get_by_industry(self, industry: str) -> List[StockBasic]:
        """根据行业获取股票列表"""
        try:
            return self.session.query(StockBasic).filter(StockBasic.industry == industry).all()
        except Exception as e:
            logger.error(f"根据行业获取股票列表失败: {e}")
            raise
    
    def update(self, ts_code: str, update_data: Dict[str, Any]) -> Optional[StockBasic]:
        """更新股票基础信息"""
        try:
            stock = self.get_by_ts_code(ts_code)
            if stock:
                for key, value in update_data.items():
                    if hasattr(stock, key):
                        setattr(stock, key, value)
                stock.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新股票基础信息成功: {ts_code}")
                return stock
            else:
                logger.warning(f"未找到要更新的股票: {ts_code}")
                return None
        except Exception as e:
            self.session.rollback()
            logger.error(f"更新股票基础信息失败: {e}")
            raise
    
    def delete(self, ts_code: str) -> bool:
        """删除股票基础信息"""
        try:
            stock = self.get_by_ts_code(ts_code)
            if stock:
                self.session.delete(stock)
                self.session.commit()
                logger.info(f"删除股票基础信息成功: {ts_code}")
                return True
            else:
                logger.warning(f"未找到要删除的股票: {ts_code}")
                return False
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除股票基础信息失败: {e}")
            raise
    
    def upsert(self, stock_data: Dict[str, Any]) -> StockBasic:
        """插入或更新股票基础信息"""
        try:
            ts_code = stock_data.get('ts_code')
            existing_stock = self.get_by_ts_code(ts_code)
            
            if existing_stock:
                # 更新现有记录
                for key, value in stock_data.items():
                    if hasattr(existing_stock, key):
                        setattr(existing_stock, key, value)
                existing_stock.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新股票基础信息成功: {ts_code}")
                return existing_stock
            else:
                # 创建新记录
                return self.create(stock_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新股票基础信息失败: {e}")
            raise
    
    def bulk_upsert(self, stocks_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新股票基础信息"""
        try:
            updated_count = 0
            created_count = 0
            
            for stock_data in stocks_data:
                ts_code = stock_data.get('ts_code')
                existing_stock = self.get_by_ts_code(ts_code)
                
                if existing_stock:
                    # 更新现有记录
                    for key, value in stock_data.items():
                        if hasattr(existing_stock, key):
                            setattr(existing_stock, key, value)
                    existing_stock.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    stock = StockBasic(**stock_data)
                    self.session.add(stock)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新股票基础信息成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新股票基础信息失败: {e}")
            raise
    
    def get_count(self) -> int:
        """获取股票总数"""
        try:
            return self.session.query(StockBasic).count()
        except Exception as e:
            logger.error(f"获取股票总数失败: {e}")
            raise
    
    def search_by_name(self, name: str) -> List[StockBasic]:
        """根据股票名称搜索"""
        try:
            return self.session.query(StockBasic).filter(
                StockBasic.name.like(f'%{name}%')
            ).all()
        except Exception as e:
            logger.error(f"根据股票名称搜索失败: {e}")
            raise
    
    def get_recently_listed(self, days: int = 30) -> List[StockBasic]:
        """获取最近上市的股票"""
        try:
            from datetime import date, timedelta
            cutoff_date = date.today() - timedelta(days=days)
            return self.session.query(StockBasic).filter(
                and_(
                    StockBasic.list_date >= cutoff_date,
                    StockBasic.list_status == 'L'
                )
            ).all()
        except Exception as e:
            logger.error(f"获取最近上市股票失败: {e}")
            raise
