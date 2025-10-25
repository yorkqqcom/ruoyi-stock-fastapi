"""
A股复权行情数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.adjusted_quote import AdjustedQuote
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import pandas as pd
from datetime import datetime, date

class AdjustedQuoteDAO:
    """A股复权行情数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, quote_data: Dict[str, Any]) -> AdjustedQuote:
        """创建复权行情记录"""
        try:
            quote = AdjustedQuote(**quote_data)
            self.session.add(quote)
            self.session.commit()
            logger.info(f"创建复权行情记录成功: {quote.ts_code} - {quote.trade_date} - {quote.adj_type}")
            return quote
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建复权行情记录失败: {e}")
            raise
    
    def bulk_create(self, quotes_data: List[Dict[str, Any]]) -> int:
        """批量创建复权行情记录"""
        try:
            quotes = [AdjustedQuote(**data) for data in quotes_data]
            self.session.add_all(quotes)
            self.session.commit()
            logger.info(f"批量创建复权行情记录成功，共 {len(quotes)} 条记录")
            return len(quotes)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建复权行情记录失败: {e}")
            raise
    
    def get_by_ts_code_and_adj(self, ts_code: str, adj_type: str, start_date: Optional[date] = None, 
                              end_date: Optional[date] = None) -> List[AdjustedQuote]:
        """根据股票代码和复权类型获取数据"""
        try:
            query = self.session.query(AdjustedQuote).filter(
                AdjustedQuote.ts_code == ts_code,
                AdjustedQuote.adj_type == adj_type
            )
            if start_date:
                query = query.filter(AdjustedQuote.trade_date >= start_date)
            if end_date:
                query = query.filter(AdjustedQuote.trade_date <= end_date)
            return query.order_by(AdjustedQuote.trade_date.desc()).all()
        except Exception as e:
            logger.error(f"根据股票代码和复权类型获取数据失败: {e}")
            raise
    
    def get_by_trade_date_and_adj(self, trade_date: date, adj_type: str) -> List[AdjustedQuote]:
        """根据交易日期和复权类型获取所有股票数据"""
        try:
            return self.session.query(AdjustedQuote).filter(
                AdjustedQuote.trade_date == trade_date,
                AdjustedQuote.adj_type == adj_type
            ).all()
        except Exception as e:
            logger.error(f"根据交易日期和复权类型获取数据失败: {e}")
            raise
    
    def get_latest_trade_date(self, adj_type: str) -> Optional[date]:
        """获取指定复权类型的最新交易日期"""
        try:
            result = self.session.query(AdjustedQuote.trade_date).filter(
                AdjustedQuote.adj_type == adj_type
            ).order_by(AdjustedQuote.trade_date.desc()).first()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
    
    def get_date_range(self, adj_type: str) -> Tuple[Optional[date], Optional[date]]:
        """获取指定复权类型的数据日期范围"""
        try:
            min_date = self.session.query(AdjustedQuote.trade_date).filter(
                AdjustedQuote.adj_type == adj_type
            ).order_by(AdjustedQuote.trade_date.asc()).first()
            max_date = self.session.query(AdjustedQuote.trade_date).filter(
                AdjustedQuote.adj_type == adj_type
            ).order_by(AdjustedQuote.trade_date.desc()).first()
            return (min_date[0] if min_date else None, max_date[0] if max_date else None)
        except Exception as e:
            logger.error(f"获取数据日期范围失败: {e}")
            raise
    
    def upsert(self, quote_data: Dict[str, Any]) -> AdjustedQuote:
        """插入或更新复权行情记录"""
        try:
            ts_code = quote_data.get('ts_code')
            trade_date = quote_data.get('trade_date')
            adj_type = quote_data.get('adj_type')
            
            existing_quote = self.session.query(AdjustedQuote).filter(
                AdjustedQuote.ts_code == ts_code,
                AdjustedQuote.trade_date == trade_date,
                AdjustedQuote.adj_type == adj_type
            ).first()
            
            if existing_quote:
                # 更新现有记录
                for key, value in quote_data.items():
                    if hasattr(existing_quote, key):
                        setattr(existing_quote, key, value)
                existing_quote.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新复权行情记录成功: {ts_code} - {trade_date} - {adj_type}")
                return existing_quote
            else:
                # 创建新记录
                return self.create(quote_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新复权行情记录失败: {e}")
            raise
    
    def bulk_upsert(self, quotes_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新复权行情记录"""
        try:
            updated_count = 0
            created_count = 0
            
            for quote_data in quotes_data:
                ts_code = quote_data.get('ts_code')
                trade_date = quote_data.get('trade_date')
                adj_type = quote_data.get('adj_type')
                
                existing_quote = self.session.query(AdjustedQuote).filter(
                    AdjustedQuote.ts_code == ts_code,
                    AdjustedQuote.trade_date == trade_date,
                    AdjustedQuote.adj_type == adj_type
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
                    quote = AdjustedQuote(**quote_data)
                    self.session.add(quote)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新复权行情记录成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新复权行情记录失败: {e}")
            raise
    
    def delete_by_trade_date_and_adj(self, trade_date: date, adj_type: str) -> int:
        """删除指定交易日和复权类型的所有数据"""
        try:
            deleted_count = self.session.query(AdjustedQuote).filter(
                AdjustedQuote.trade_date == trade_date,
                AdjustedQuote.adj_type == adj_type
            ).delete()
            self.session.commit()
            logger.info(f"删除交易日 {trade_date} 复权类型 {adj_type} 的数据成功，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除交易日数据失败: {e}")
            raise
    
    def get_count(self, ts_code: Optional[str] = None, adj_type: Optional[str] = None, 
                 start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """获取记录总数"""
        try:
            query = self.session.query(AdjustedQuote)
            if ts_code:
                query = query.filter(AdjustedQuote.ts_code == ts_code)
            if adj_type:
                query = query.filter(AdjustedQuote.adj_type == adj_type)
            if start_date:
                query = query.filter(AdjustedQuote.trade_date >= start_date)
            if end_date:
                query = query.filter(AdjustedQuote.trade_date <= end_date)
            return query.count()
        except Exception as e:
            logger.error(f"获取记录总数失败: {e}")
            raise
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            # 总记录数
            total_count = self.get_count()
            
            # 按复权类型统计
            adj_type_stats = self.session.query(
                AdjustedQuote.adj_type,
                func.count(AdjustedQuote.id).label('count')
            ).group_by(AdjustedQuote.adj_type).all()
            
            # 按年份统计
            yearly_stats = self.session.query(
                func.year(AdjustedQuote.trade_date).label('year'),
                func.count(AdjustedQuote.id).label('count')
            ).group_by(func.year(AdjustedQuote.trade_date)).all()
            
            # 股票数量
            stock_count = self.session.query(func.count(func.distinct(AdjustedQuote.ts_code))).scalar()
            
            # 日期范围
            date_range = self.session.query(
                func.min(AdjustedQuote.trade_date),
                func.max(AdjustedQuote.trade_date)
            ).first()
            
            statistics = {
                'total_count': total_count,
                'stock_count': stock_count,
                'adj_type_stats': {row.adj_type: row.count for row in adj_type_stats},
                'yearly_stats': {str(row.year): row.count for row in yearly_stats},
                'date_range': {
                    'start_date': date_range[0],
                    'end_date': date_range[1]
                },
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取复权行情统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取复权行情统计信息失败: {e}")
            raise
    
    def is_data_exists(self, ts_code: str, trade_date: date, adj_type: str) -> bool:
        """检查指定股票、交易日和复权类型的数据是否存在"""
        try:
            count = self.session.query(AdjustedQuote).filter(
                AdjustedQuote.ts_code == ts_code,
                AdjustedQuote.trade_date == trade_date,
                AdjustedQuote.adj_type == adj_type
            ).count()
            return count > 0
        except Exception as e:
            logger.error(f"检查数据是否存在失败: {e}")
            raise
    
    def get_missing_data(self, ts_codes: List[str], start_date: date, end_date: date, 
                        adj_types: List[str]) -> List[Dict[str, Any]]:
        """获取缺失的数据列表"""
        try:
            missing_data = []
            
            for ts_code in ts_codes:
                for adj_type in adj_types:
                    # 检查该股票和复权类型是否有数据
                    count = self.session.query(AdjustedQuote).filter(
                        AdjustedQuote.ts_code == ts_code,
                        AdjustedQuote.adj_type == adj_type,
                        AdjustedQuote.trade_date >= start_date,
                        AdjustedQuote.trade_date <= end_date
                    ).count()
                    
                    if count == 0:
                        missing_data.append({
                            'ts_code': ts_code,
                            'adj_type': adj_type,
                            'start_date': start_date,
                            'end_date': end_date
                        })
            
            return missing_data
            
        except Exception as e:
            logger.error(f"获取缺失数据列表失败: {e}")
            raise
    
    def get_stocks_with_data(self) -> List[str]:
        """获取已有复权数据的股票代码列表"""
        try:
            stocks = self.session.query(
                func.distinct(AdjustedQuote.ts_code)
            ).all()
            return [stock[0] for stock in stocks]
        except Exception as e:
            logger.error(f"获取已有数据股票列表失败: {e}")
            return []
    
    def get_daily_stock_count(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """获取每个交易日的股票数量统计"""
        try:
            results = self.session.query(
                AdjustedQuote.trade_date,
                func.count(func.distinct(AdjustedQuote.ts_code)).label('stock_count')
            ).filter(
                AdjustedQuote.trade_date >= start_date,
                AdjustedQuote.trade_date <= end_date
            ).group_by(AdjustedQuote.trade_date).order_by(AdjustedQuote.trade_date).all()
            
            return [
                {
                    'trade_date': result.trade_date,
                    'stock_count': result.stock_count
                }
                for result in results
            ]
        except Exception as e:
            logger.error(f"获取每日股票数量统计失败: {e}")
            return []

    def get_sync_progress(self, adj_types: List[str]) -> Dict[str, Any]:
        """获取同步进度信息"""
        try:
            progress = {}
            
            for adj_type in adj_types:
                # 获取该复权类型的统计信息
                count = self.get_count(adj_type=adj_type)
                date_range = self.get_date_range(adj_type)
                
                progress[adj_type] = {
                    'count': count,
                    'date_range': date_range
                }
            
            return progress
            
        except Exception as e:
            logger.error(f"获取同步进度信息失败: {e}")
            raise
