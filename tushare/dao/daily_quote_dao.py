"""
A股日线行情数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.daily_quote import DailyQuote
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import pandas as pd
from datetime import datetime, date

class DailyQuoteDAO:
    """A股日线行情数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, quote_data: Dict[str, Any]) -> DailyQuote:
        """创建日线行情记录"""
        try:
            quote = DailyQuote(**quote_data)
            self.session.add(quote)
            self.session.commit()
            logger.info(f"创建日线行情记录成功: {quote.ts_code} - {quote.trade_date}")
            return quote
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建日线行情记录失败: {e}")
            raise
    
    def bulk_create(self, quotes_data: List[Dict[str, Any]]) -> int:
        """批量创建日线行情记录"""
        try:
            quotes = [DailyQuote(**data) for data in quotes_data]
            self.session.add_all(quotes)
            self.session.commit()
            logger.info(f"批量创建日线行情记录成功，共 {len(quotes)} 条记录")
            return len(quotes)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建日线行情记录失败: {e}")
            raise
    
    def get_by_ts_code(self, ts_code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> List[DailyQuote]:
        """根据股票代码获取日线数据"""
        try:
            query = self.session.query(DailyQuote).filter(DailyQuote.ts_code == ts_code)
            if start_date:
                query = query.filter(DailyQuote.trade_date >= start_date)
            if end_date:
                query = query.filter(DailyQuote.trade_date <= end_date)
            return query.order_by(DailyQuote.trade_date.desc()).all()
        except Exception as e:
            logger.error(f"根据股票代码获取日线数据失败: {e}")
            raise
    
    def get_by_trade_date(self, trade_date: date) -> List[DailyQuote]:
        """根据交易日期获取所有股票数据"""
        try:
            return self.session.query(DailyQuote).filter(DailyQuote.trade_date == trade_date).all()
        except Exception as e:
            logger.error(f"根据交易日期获取日线数据失败: {e}")
            raise
    
    def get_latest_trade_date(self) -> Optional[date]:
        """获取最新的交易日期"""
        try:
            result = self.session.query(DailyQuote.trade_date).order_by(DailyQuote.trade_date.desc()).first()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
    
    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """获取数据日期范围"""
        try:
            min_date = self.session.query(DailyQuote.trade_date).order_by(DailyQuote.trade_date.asc()).first()
            max_date = self.session.query(DailyQuote.trade_date).order_by(DailyQuote.trade_date.desc()).first()
            return (min_date[0] if min_date else None, max_date[0] if max_date else None)
        except Exception as e:
            logger.error(f"获取数据日期范围失败: {e}")
            raise
    
    def upsert(self, quote_data: Dict[str, Any]) -> DailyQuote:
        """插入或更新日线行情记录"""
        try:
            ts_code = quote_data.get('ts_code')
            trade_date = quote_data.get('trade_date')
            
            existing_quote = self.session.query(DailyQuote).filter(
                DailyQuote.ts_code == ts_code,
                DailyQuote.trade_date == trade_date
            ).first()
            
            if existing_quote:
                # 更新现有记录
                for key, value in quote_data.items():
                    if hasattr(existing_quote, key):
                        setattr(existing_quote, key, value)
                existing_quote.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新日线行情记录成功: {ts_code} - {trade_date}")
                return existing_quote
            else:
                # 创建新记录
                return self.create(quote_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新日线行情记录失败: {e}")
            raise
    
    def bulk_upsert(self, quotes_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新日线行情记录"""
        try:
            updated_count = 0
            created_count = 0
            
            for quote_data in quotes_data:
                ts_code = quote_data.get('ts_code')
                trade_date = quote_data.get('trade_date')
                
                existing_quote = self.session.query(DailyQuote).filter(
                    DailyQuote.ts_code == ts_code,
                    DailyQuote.trade_date == trade_date
                ).first()
                
                if existing_quote:
                    # 更新现有记录
                    for key, value in quote_data.items():
                        if hasattr(existing_quote, key):
                            setattr(existing_quote, key, value)
                    existing_quote.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    quote = DailyQuote(**quote_data)
                    self.session.add(quote)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新日线行情记录成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新日线行情记录失败: {e}")
            raise
    
    def delete_by_trade_date(self, trade_date: date) -> int:
        """删除指定交易日的所有数据"""
        try:
            deleted_count = self.session.query(DailyQuote).filter(DailyQuote.trade_date == trade_date).delete()
            self.session.commit()
            logger.info(f"删除交易日 {trade_date} 的数据成功，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除交易日数据失败: {e}")
            raise
    
    def get_count(self, ts_code: Optional[str] = None, start_date: Optional[date] = None, 
                 end_date: Optional[date] = None) -> int:
        """获取记录总数"""
        try:
            query = self.session.query(DailyQuote)
            if ts_code:
                query = query.filter(DailyQuote.ts_code == ts_code)
            if start_date:
                query = query.filter(DailyQuote.trade_date >= start_date)
            if end_date:
                query = query.filter(DailyQuote.trade_date <= end_date)
            return query.count()
        except Exception as e:
            logger.error(f"获取记录总数失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 总记录数
            total_count = self.get_count()
            
            # 日期范围
            min_date, max_date = self.get_date_range()
            
            # 股票数量
            stock_count = self.session.query(func.count(func.distinct(DailyQuote.ts_code))).scalar()
            
            # 按年份统计
            yearly_stats = self.session.query(
                func.year(DailyQuote.trade_date).label('year'),
                func.count(DailyQuote.id).label('count')
            ).group_by(func.year(DailyQuote.trade_date)).all()
            
            statistics = {
                'total_count': total_count,
                'stock_count': stock_count,
                'date_range': {
                    'start_date': min_date,
                    'end_date': max_date
                },
                'yearly_stats': {str(row.year): row.count for row in yearly_stats},
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取日线行情统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取日线行情统计信息失败: {e}")
            raise
    
    def is_data_exists(self, trade_date: date) -> bool:
        """检查指定交易日数据是否存在"""
        try:
            count = self.session.query(DailyQuote).filter(DailyQuote.trade_date == trade_date).count()
            return count > 0
        except Exception as e:
            logger.error(f"检查交易日数据是否存在失败: {e}")
            raise
    
    def get_missing_trading_days(self, start_date: date, end_date: date, 
                               trading_days: List[date]) -> List[date]:
        """获取缺失的交易日列表"""
        try:
            # 获取已存在的交易日
            existing_dates = self.session.query(DailyQuote.trade_date).filter(
                DailyQuote.trade_date >= start_date,
                DailyQuote.trade_date <= end_date
            ).distinct().all()
            
            existing_dates_set = {row[0] for row in existing_dates}
            
            # 找出缺失的交易日
            missing_days = [day for day in trading_days if day not in existing_dates_set]
            
            return missing_days
            
        except Exception as e:
            logger.error(f"获取缺失交易日列表失败: {e}")
            raise
