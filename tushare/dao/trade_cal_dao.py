"""
交易日历数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from models.trade_cal import TradeCal
from typing import List, Optional, Dict, Any
from loguru import logger
import pandas as pd
from datetime import datetime, date

class TradeCalDAO:
    """交易日历数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, trade_cal_data: Dict[str, Any]) -> TradeCal:
        """创建交易日历记录"""
        try:
            trade_cal = TradeCal(**trade_cal_data)
            self.session.add(trade_cal)
            self.session.commit()
            logger.info(f"创建交易日历记录成功: {trade_cal.exchange} - {trade_cal.cal_date}")
            return trade_cal
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建交易日历记录失败: {e}")
            raise
    
    def bulk_create(self, trade_cals_data: List[Dict[str, Any]]) -> int:
        """批量创建交易日历记录"""
        try:
            trade_cals = [TradeCal(**data) for data in trade_cals_data]
            self.session.add_all(trade_cals)
            self.session.commit()
            logger.info(f"批量创建交易日历记录成功，共 {len(trade_cals)} 条记录")
            return len(trade_cals)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建交易日历记录失败: {e}")
            raise
    
    def get_by_exchange(self, exchange: str) -> List[TradeCal]:
        """根据交易所获取交易日历"""
        try:
            return self.session.query(TradeCal).filter(TradeCal.exchange == exchange).order_by(TradeCal.cal_date).all()
        except Exception as e:
            logger.error(f"根据交易所获取交易日历失败: {e}")
            raise
    
    def get_by_date_range(self, start_date: date, end_date: date, exchange: Optional[str] = None) -> List[TradeCal]:
        """根据日期范围获取交易日历"""
        try:
            query = self.session.query(TradeCal).filter(
                TradeCal.cal_date >= start_date, 
                TradeCal.cal_date <= end_date
            )
            if exchange:
                query = query.filter(TradeCal.exchange == exchange)
            return query.order_by(TradeCal.cal_date).all()
        except Exception as e:
            logger.error(f"根据日期范围获取交易日历失败: {e}")
            raise
    
    def get_trading_days(self, start_date: date, end_date: date, exchange: Optional[str] = None) -> List[TradeCal]:
        """获取交易日列表"""
        try:
            query = self.session.query(TradeCal).filter(
                TradeCal.cal_date >= start_date, 
                TradeCal.cal_date <= end_date,
                TradeCal.is_open == '1'
            )
            if exchange:
                query = query.filter(TradeCal.exchange == exchange)
            return query.order_by(TradeCal.cal_date).all()
        except Exception as e:
            logger.error(f"获取交易日列表失败: {e}")
            raise
    
    def get_non_trading_days(self, start_date: date, end_date: date, exchange: Optional[str] = None) -> List[TradeCal]:
        """获取非交易日列表"""
        try:
            query = self.session.query(TradeCal).filter(
                TradeCal.cal_date >= start_date, 
                TradeCal.cal_date <= end_date,
                TradeCal.is_open == '0'
            )
            if exchange:
                query = query.filter(TradeCal.exchange == exchange)
            return query.order_by(TradeCal.cal_date).all()
        except Exception as e:
            logger.error(f"获取非交易日列表失败: {e}")
            raise
    
    def upsert(self, trade_cal_data: Dict[str, Any]) -> TradeCal:
        """插入或更新交易日历记录"""
        try:
            exchange = trade_cal_data.get('exchange')
            cal_date = trade_cal_data.get('cal_date')
            existing_record = self.session.query(TradeCal).filter(
                TradeCal.exchange == exchange,
                TradeCal.cal_date == cal_date
            ).first()
            
            if existing_record:
                # 更新现有记录
                for key, value in trade_cal_data.items():
                    if hasattr(existing_record, key):
                        setattr(existing_record, key, value)
                existing_record.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新交易日历记录成功: {exchange} - {cal_date}")
                return existing_record
            else:
                # 创建新记录
                return self.create(trade_cal_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新交易日历记录失败: {e}")
            raise
    
    def bulk_upsert(self, trade_cals_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新交易日历记录"""
        try:
            updated_count = 0
            created_count = 0
            
            for trade_cal_data in trade_cals_data:
                exchange = trade_cal_data.get('exchange')
                cal_date = trade_cal_data.get('cal_date')
                existing_record = self.session.query(TradeCal).filter(
                    TradeCal.exchange == exchange,
                    TradeCal.cal_date == cal_date
                ).first()
                
                if existing_record:
                    # 更新现有记录
                    for key, value in trade_cal_data.items():
                        if hasattr(existing_record, key):
                            setattr(existing_record, key, value)
                    existing_record.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    trade_cal = TradeCal(**trade_cal_data)
                    self.session.add(trade_cal)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新交易日历记录成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新交易日历记录失败: {e}")
            raise
    
    def get_count(self, exchange: Optional[str] = None) -> int:
        """获取交易日历记录总数"""
        try:
            query = self.session.query(TradeCal)
            if exchange:
                query = query.filter(TradeCal.exchange == exchange)
            return query.count()
        except Exception as e:
            logger.error(f"获取交易日历记录总数失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取交易日历统计信息"""
        try:
            from sqlalchemy import func
            
            # 按交易所统计
            exchange_stats = self.session.query(
                TradeCal.exchange, 
                func.count(TradeCal.id)
            ).group_by(TradeCal.exchange).all()
            
            # 按交易状态统计
            trading_stats = self.session.query(
                TradeCal.is_open, 
                func.count(TradeCal.id)
            ).group_by(TradeCal.is_open).all()
            
            # 日期范围
            date_range = self.session.query(
                func.min(TradeCal.cal_date),
                func.max(TradeCal.cal_date)
            ).first()
            
            statistics = {
                'total_count': self.get_count(),
                'exchange_stats': dict(exchange_stats),
                'trading_stats': dict(trading_stats),
                'date_range': {
                    'start_date': date_range[0],
                    'end_date': date_range[1]
                },
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取交易日历统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取交易日历统计信息失败: {e}")
            raise
