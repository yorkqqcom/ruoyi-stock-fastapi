"""
个股资金流向数据访问层
"""
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.moneyflow import MoneyFlow
from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
import pandas as pd
from datetime import datetime, date

class MoneyFlowDAO:
    """个股资金流向数据访问对象"""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, moneyflow_data: Dict[str, Any]) -> MoneyFlow:
        """创建资金流向记录"""
        try:
            moneyflow = MoneyFlow(**moneyflow_data)
            self.session.add(moneyflow)
            self.session.commit()
            logger.info(f"创建资金流向记录成功: {moneyflow.ts_code} - {moneyflow.trade_date}")
            return moneyflow
        except Exception as e:
            self.session.rollback()
            logger.error(f"创建资金流向记录失败: {e}")
            raise
    
    def bulk_create(self, moneyflows_data: List[Dict[str, Any]]) -> int:
        """批量创建资金流向记录"""
        try:
            moneyflows = [MoneyFlow(**data) for data in moneyflows_data]
            self.session.add_all(moneyflows)
            self.session.commit()
            logger.info(f"批量创建资金流向记录成功，共 {len(moneyflows)} 条记录")
            return len(moneyflows)
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量创建资金流向记录失败: {e}")
            raise
    
    def get_by_ts_code(self, ts_code: str, start_date: Optional[date] = None, 
                      end_date: Optional[date] = None) -> List[MoneyFlow]:
        """根据股票代码获取资金流向数据"""
        try:
            query = self.session.query(MoneyFlow).filter(MoneyFlow.ts_code == ts_code)
            if start_date:
                query = query.filter(MoneyFlow.trade_date >= start_date)
            if end_date:
                query = query.filter(MoneyFlow.trade_date <= end_date)
            return query.order_by(MoneyFlow.trade_date.desc()).all()
        except Exception as e:
            logger.error(f"根据股票代码获取资金流向数据失败: {e}")
            raise
    
    def get_by_trade_date(self, trade_date: date) -> List[MoneyFlow]:
        """根据交易日期获取所有股票资金流向数据"""
        try:
            return self.session.query(MoneyFlow).filter(MoneyFlow.trade_date == trade_date).all()
        except Exception as e:
            logger.error(f"根据交易日期获取资金流向数据失败: {e}")
            raise
    
    def get_latest_trade_date(self) -> Optional[date]:
        """获取最新的交易日期"""
        try:
            result = self.session.query(MoneyFlow.trade_date).order_by(MoneyFlow.trade_date.desc()).first()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"获取最新交易日期失败: {e}")
            raise
    
    def get_date_range(self) -> Tuple[Optional[date], Optional[date]]:
        """获取数据日期范围"""
        try:
            min_date = self.session.query(MoneyFlow.trade_date).order_by(MoneyFlow.trade_date.asc()).first()
            max_date = self.session.query(MoneyFlow.trade_date).order_by(MoneyFlow.trade_date.desc()).first()
            return (min_date[0] if min_date else None, max_date[0] if max_date else None)
        except Exception as e:
            logger.error(f"获取数据日期范围失败: {e}")
            raise
    
    def upsert(self, moneyflow_data: Dict[str, Any]) -> MoneyFlow:
        """插入或更新资金流向记录"""
        try:
            ts_code = moneyflow_data.get('ts_code')
            trade_date = moneyflow_data.get('trade_date')
            
            existing_moneyflow = self.session.query(MoneyFlow).filter(
                MoneyFlow.ts_code == ts_code,
                MoneyFlow.trade_date == trade_date
            ).first()
            
            if existing_moneyflow:
                # 更新现有记录
                for key, value in moneyflow_data.items():
                    if hasattr(existing_moneyflow, key):
                        setattr(existing_moneyflow, key, value)
                existing_moneyflow.updated_at = datetime.now()
                self.session.commit()
                logger.info(f"更新资金流向记录成功: {ts_code} - {trade_date}")
                return existing_moneyflow
            else:
                # 创建新记录
                return self.create(moneyflow_data)
        except Exception as e:
            self.session.rollback()
            logger.error(f"插入或更新资金流向记录失败: {e}")
            raise
    
    def bulk_upsert(self, moneyflows_data: List[Dict[str, Any]]) -> int:
        """批量插入或更新资金流向记录"""
        try:
            updated_count = 0
            created_count = 0
            
            for moneyflow_data in moneyflows_data:
                ts_code = moneyflow_data.get('ts_code')
                trade_date = moneyflow_data.get('trade_date')
                
                existing_moneyflow = self.session.query(MoneyFlow).filter(
                    MoneyFlow.ts_code == ts_code,
                    MoneyFlow.trade_date == trade_date
                ).first()
                
                if existing_moneyflow:
                    # 更新现有记录
                    for key, value in moneyflow_data.items():
                        if hasattr(existing_moneyflow, key):
                            setattr(existing_moneyflow, key, value)
                    existing_moneyflow.updated_at = datetime.now()
                    updated_count += 1
                else:
                    # 创建新记录
                    moneyflow = MoneyFlow(**moneyflow_data)
                    self.session.add(moneyflow)
                    created_count += 1
            
            self.session.commit()
            logger.info(f"批量插入或更新资金流向记录成功，创建 {created_count} 条，更新 {updated_count} 条")
            return created_count + updated_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"批量插入或更新资金流向记录失败: {e}")
            raise
    
    def delete_by_trade_date(self, trade_date: date) -> int:
        """删除指定交易日的所有数据"""
        try:
            deleted_count = self.session.query(MoneyFlow).filter(MoneyFlow.trade_date == trade_date).delete()
            self.session.commit()
            logger.info(f"删除交易日 {trade_date} 的资金流向数据成功，共删除 {deleted_count} 条记录")
            return deleted_count
        except Exception as e:
            self.session.rollback()
            logger.error(f"删除交易日资金流向数据失败: {e}")
            raise
    
    def get_count(self, ts_code: Optional[str] = None, start_date: Optional[date] = None, 
                 end_date: Optional[date] = None) -> int:
        """获取记录总数"""
        try:
            query = self.session.query(MoneyFlow)
            if ts_code:
                query = query.filter(MoneyFlow.ts_code == ts_code)
            if start_date:
                query = query.filter(MoneyFlow.trade_date >= start_date)
            if end_date:
                query = query.filter(MoneyFlow.trade_date <= end_date)
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
            stock_count = self.session.query(func.count(func.distinct(MoneyFlow.ts_code))).scalar()
            
            # 按年份统计
            yearly_stats = self.session.query(
                func.year(MoneyFlow.trade_date).label('year'),
                func.count(MoneyFlow.id).label('count')
            ).group_by(func.year(MoneyFlow.trade_date)).all()
            
            # 净流入统计
            net_inflow_stats = self.session.query(
                func.sum(MoneyFlow.net_mf_amount).label('total_net_inflow'),
                func.avg(MoneyFlow.net_mf_amount).label('avg_net_inflow'),
                func.max(MoneyFlow.net_mf_amount).label('max_net_inflow'),
                func.min(MoneyFlow.net_mf_amount).label('min_net_inflow')
            ).filter(MoneyFlow.net_mf_amount.isnot(None)).first()
            
            statistics = {
                'total_count': total_count,
                'stock_count': stock_count,
                'date_range': {
                    'start_date': min_date,
                    'end_date': max_date
                },
                'yearly_stats': {str(row.year): row.count for row in yearly_stats},
                'net_inflow_stats': {
                    'total_net_inflow': float(net_inflow_stats.total_net_inflow) if net_inflow_stats.total_net_inflow else 0,
                    'avg_net_inflow': float(net_inflow_stats.avg_net_inflow) if net_inflow_stats.avg_net_inflow else 0,
                    'max_net_inflow': float(net_inflow_stats.max_net_inflow) if net_inflow_stats.max_net_inflow else 0,
                    'min_net_inflow': float(net_inflow_stats.min_net_inflow) if net_inflow_stats.min_net_inflow else 0
                },
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取资金流向统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取资金流向统计信息失败: {e}")
            raise
    
    def is_data_exists(self, trade_date: date) -> bool:
        """检查指定交易日数据是否存在"""
        try:
            count = self.session.query(MoneyFlow).filter(MoneyFlow.trade_date == trade_date).count()
            return count > 0
        except Exception as e:
            logger.error(f"检查交易日资金流向数据是否存在失败: {e}")
            raise
    
    def get_missing_trading_days(self, start_date: date, end_date: date, 
                               trading_days: List[date]) -> List[date]:
        """获取缺失的交易日列表"""
        try:
            # 获取已存在的交易日
            existing_dates = self.session.query(MoneyFlow.trade_date).filter(
                MoneyFlow.trade_date >= start_date,
                MoneyFlow.trade_date <= end_date
            ).distinct().all()
            
            existing_dates_set = {row[0] for row in existing_dates}
            
            # 找出缺失的交易日
            missing_days = [day for day in trading_days if day not in existing_dates_set]
            
            return missing_days
            
        except Exception as e:
            logger.error(f"获取缺失交易日列表失败: {e}")
            raise
    
    def get_top_net_inflow(self, trade_date: date, limit: int = 20) -> List[MoneyFlow]:
        """获取指定日期净流入额最高的股票"""
        try:
            return self.session.query(MoneyFlow).filter(
                MoneyFlow.trade_date == trade_date,
                MoneyFlow.net_mf_amount > 0
            ).order_by(MoneyFlow.net_mf_amount.desc()).limit(limit).all()
        except Exception as e:
            logger.error(f"获取净流入额最高股票失败: {e}")
            raise
    
    def get_top_net_outflow(self, trade_date: date, limit: int = 20) -> List[MoneyFlow]:
        """获取指定日期净流出额最高的股票"""
        try:
            return self.session.query(MoneyFlow).filter(
                MoneyFlow.trade_date == trade_date,
                MoneyFlow.net_mf_amount < 0
            ).order_by(MoneyFlow.net_mf_amount.asc()).limit(limit).all()
        except Exception as e:
            logger.error(f"获取净流出额最高股票失败: {e}")
            raise
    
    def get_net_inflow_by_date_range(self, start_date: date, end_date: date, 
                                   ts_code: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取指定日期范围内的净流入数据"""
        try:
            query = self.session.query(
                MoneyFlow.trade_date,
                MoneyFlow.ts_code,
                MoneyFlow.net_mf_amount
            ).filter(
                MoneyFlow.trade_date >= start_date,
                MoneyFlow.trade_date <= end_date
            )
            
            if ts_code:
                query = query.filter(MoneyFlow.ts_code == ts_code)
            
            results = query.order_by(MoneyFlow.trade_date.desc()).all()
            
            return [
                {
                    'trade_date': row.trade_date,
                    'ts_code': row.ts_code,
                    'net_mf_amount': float(row.net_mf_amount) if row.net_mf_amount else 0
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"获取净流入数据失败: {e}")
            raise
