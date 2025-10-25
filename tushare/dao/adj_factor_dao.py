"""
A股复权因子数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.adj_factor import AdjFactor
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import pandas as pd
from datetime import datetime, date

class AdjFactorDAO:
    """A股复权因子数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, adj_factor_data: Dict[str, Any]) -> AdjFactor:
        """创建复权因子记录"""
        try:
            adj_factor = AdjFactor(**adj_factor_data)
            self.session.add(adj_factor)
            self.session.commit()
            logger.info(f"创建复权因子记录成功: {adj_factor.ts_code} - {adj_factor.trade_date}")
            return adj_factor
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建复权因子记录失败: {e}")
            raise
    
    def bulk_create(self, adj_factors_data: List[Dict[str, Any]]) -> int:
        """批量创建复权因子记录"""
        try:
            adj_factors = [AdjFactor(**data) for data in adj_factors_data]
            self.session.add_all(adj_factors)
            self.session.commit()
            logger.info(f"批量创建复权因子记录成功，共 {len(adj_factors)} 条记录")
            return len(adj_factors)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建复权因子记录失败: {e}")
            raise
    
    def get_by_ts_code(self, ts_code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> List[AdjFactor]:
        """根据股票代码获取复权因子"""
        try:
            query = self.session.query(AdjFactor).filter(AdjFactor.ts_code == ts_code)
            if start_date:
                query = query.filter(AdjFactor.trade_date >= start_date)
            if end_date:
                query = query.filter(AdjFactor.trade_date <= end_date)
            return query.order_by(AdjFactor.trade_date.desc()).all()
        except Exception as e:
            logger.error(f"根据股票代码获取复权因子失败: {e}")
            raise
    
    def get_by_trade_date(self, trade_date: date) -> List[AdjFactor]:
        """根据交易日期获取所有股票复权因子"""
        try:
            return self.session.query(AdjFactor).filter(AdjFactor.trade_date == trade_date).all()
        except Exception as e:
            logger.error(f"根据交易日期获取复权因子失败: {e}")
            raise
    
    def get_latest_trade_date(self) -> Optional[date]:
        """获取最新的交易日期"""
        try:
            result = self.session.query(AdjFactor.trade_date).order_by(AdjFactor.trade_date.desc()).first()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
    
    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """获取数据日期范围"""
        try:
            min_date = self.session.query(AdjFactor.trade_date).order_by(AdjFactor.trade_date.asc()).first()
            max_date = self.session.query(AdjFactor.trade_date).order_by(AdjFactor.trade_date.desc()).first()
            return (min_date[0] if min_date else None, max_date[0] if max_date else None)
        except Exception as e:
            logger.error(f"获取数据日期范围失败: {e}")
            raise
    
    def upsert(self, adj_factor_data: Dict[str, Any]) -> AdjFactor:
        """插入或更新复权因子记录"""
        try:
            ts_code = adj_factor_data.get('ts_code')
            trade_date = adj_factor_data.get('trade_date')
            
            existing_factor = self.session.query(AdjFactor).filter(
                AdjFactor.ts_code == ts_code,
                AdjFactor.trade_date == trade_date
            ).first()
            
            if existing_factor:
                # 更新现有记录
                for key, value in adj_factor_data.items():
                    if hasattr(existing_factor, key):
                        setattr(existing_factor, key, value)
                existing_factor.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新复权因子记录成功: {ts_code} - {trade_date}")
                return existing_factor
            else:
                # 创建新记录
                return self.create(adj_factor_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新复权因子记录失败: {e}")
            raise
    
    def bulk_upsert(self, adj_factors_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新复权因子记录"""
        try:
            updated_count = 0
            created_count = 0
            
            for adj_factor_data in adj_factors_data:
                ts_code = adj_factor_data.get('ts_code')
                trade_date = adj_factor_data.get('trade_date')
                
                existing_factor = self.session.query(AdjFactor).filter(
                    AdjFactor.ts_code == ts_code,
                    AdjFactor.trade_date == trade_date
                ).first()
                
                if existing_factor:
                    # 更新现有记录
                    for key, value in adj_factor_data.items():
                        if hasattr(existing_factor, key):
                            setattr(existing_factor, key, value)
                    existing_factor.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    adj_factor = AdjFactor(**adj_factor_data)
                    self.session.add(adj_factor)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新复权因子记录成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新复权因子记录失败: {e}")
            raise
    
    def delete_by_trade_date(self, trade_date: date) -> int:
        """删除指定交易日的所有数据"""
        try:
            deleted_count = self.session.query(AdjFactor).filter(AdjFactor.trade_date == trade_date).delete()
            self.session.commit()
            logger.info(f"删除交易日 {trade_date} 的复权因子数据成功，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除交易日复权因子数据失败: {e}")
            raise
    
    def get_count(self, ts_code: Optional[str] = None, start_date: Optional[date] = None, 
                 end_date: Optional[date] = None) -> int:
        """获取记录总数"""
        try:
            query = self.session.query(AdjFactor)
            if ts_code:
                query = query.filter(AdjFactor.ts_code == ts_code)
            if start_date:
                query = query.filter(AdjFactor.trade_date >= start_date)
            if end_date:
                query = query.filter(AdjFactor.trade_date <= end_date)
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
            stock_count = self.session.query(func.count(func.distinct(AdjFactor.ts_code))).scalar()
            
            # 按年份统计
            yearly_stats = self.session.query(
                func.year(AdjFactor.trade_date).label('year'),
                func.count(AdjFactor.id).label('count')
            ).group_by(func.year(AdjFactor.trade_date)).all()
            
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
            
            logger.info(f"获取复权因子统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取复权因子统计信息失败: {e}")
            raise
    
    def is_data_exists(self, ts_code: str, trade_date: date) -> bool:
        """检查指定股票和交易日的复权因子是否存在"""
        try:
            count = self.session.query(AdjFactor).filter(
                AdjFactor.ts_code == ts_code,
                AdjFactor.trade_date == trade_date
            ).count()
            return count > 0
        except Exception as e:
            logger.error(f"检查复权因子是否存在失败: {e}")
            raise
    
    def get_missing_trading_days(self, start_date: date, end_date: date, 
                               trading_days: List[date]) -> List[date]:
        """获取缺失的交易日列表"""
        try:
            # 获取已存在的交易日
            existing_dates = self.session.query(AdjFactor.trade_date).filter(
                AdjFactor.trade_date >= start_date,
                AdjFactor.trade_date <= end_date
            ).distinct().all()
            
            existing_dates_set = {row[0] for row in existing_dates}
            
            # 找出缺失的交易日
            missing_days = [day for day in trading_days if day not in existing_dates_set]
            
            return missing_days
            
        except Exception as e:
            logger.error(f"获取缺失交易日列表失败: {e}")
            raise
