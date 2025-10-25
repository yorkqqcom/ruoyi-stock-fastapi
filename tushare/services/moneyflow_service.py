"""
个股资金流向服务
"""
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, date, timedelta
from dao.moneyflow_dao import MoneyFlowDAO
from dao.trade_cal_dao import TradeCalDAO
from services.tushare_service import TushareService
from services.trade_cal_service import TradeCalService
from config import config
import time

class MoneyFlowService:
    """个股资金流向服务类"""
    
    def __init__(self, tushare_service: Optional[TushareService] = None, 
                 trade_cal_service: Optional[TradeCalService] = None):
        """
        初始化资金流向服务
        
        Args:
            tushare_service: Tushare服务实例，如果不提供则创建新实例
            trade_cal_service: 交易日历服务实例，如果不提供则创建新实例
        """
        self.tushare_service = tushare_service or TushareService()
        self.trade_cal_service = trade_cal_service or TradeCalService()
    
    def sync_historical_data_optimized(self, session, start_date: str = '20140101', 
                                     end_date: str = None) -> int:
        """
        优化的历史数据同步（基于交易日历）
        
        Args:
            session: 数据库会话
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD，默认为当前日期
            
        Returns:
            同步的记录数量
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            logger.info(f"开始同步历史资金流向数据: {start_date} 到 {end_date}")
            
            # 1. 获取交易日列表（只获取交易日，跳过周末和节假日）
            trading_days = self._get_trading_days_for_polling(start_date, end_date, session)
            
            if not trading_days:
                logger.warning("未找到交易日数据，请先同步交易日历")
                return 0
            
            total_days = len(trading_days)
            logger.info(f"需要同步 {total_days} 个交易日的数据")
            
            # 2. 检查已存在的数据，避免重复同步
            dao = MoneyFlowDAO(session)
            missing_days = dao.get_missing_trading_days(
                datetime.strptime(start_date, '%Y%m%d').date(),
                datetime.strptime(end_date, '%Y%m%d').date(),
                trading_days
            )
            
            if not missing_days:
                logger.info("所有交易日数据已存在，无需同步")
                return 0
            
            logger.info(f"发现 {len(missing_days)} 个缺失的交易日，开始同步")
            
            # 3. 按交易日逐个获取数据
            total_count = 0
            for i, trade_date in enumerate(missing_days, 1):
                try:
                    logger.info(f"正在同步第 {i}/{len(missing_days)} 个交易日: {trade_date}")
                    
                    # 获取单日所有股票资金流向数据
                    daily_data = self.tushare_service.get_moneyflow_by_date(trade_date.strftime('%Y%m%d'))
                    
                    if not daily_data.empty:
                        # 数据预处理
                        processed_data = self._preprocess_dataframe(daily_data)
                        
                        # 转换为字典列表
                        moneyflows_data = processed_data.to_dict('records')
                        
                        # 批量插入到数据库
                        count = dao.bulk_upsert(moneyflows_data)
                        total_count += count
                        
                        logger.info(f"交易日 {trade_date} 同步完成，共 {len(daily_data)} 条记录")
                    else:
                        logger.warning(f"交易日 {trade_date} 无资金流向数据")
                    
                    # 控制API调用频率（资金流向接口需要更长的间隔）
                    time.sleep(0.2)
                    
                except Exception as e:
                    logger.error(f"交易日 {trade_date} 同步失败: {e}")
                    continue
            
            logger.info(f"历史资金流向数据同步完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"同步历史资金流向数据失败: {e}")
            raise
    
    def sync_daily_data_optimized(self, session) -> int:
        """
        优化的日常数据同步（获取上一个交易日数据）
        
        Args:
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info("开始日常资金流向数据同步")
            
            # 1. 获取上一个交易日
            last_trading_day = self._get_last_trading_day(session)
            
            if not last_trading_day:
                logger.warning("未找到上一个交易日")
                return 0
            
            logger.info(f"上一个交易日: {last_trading_day}")
            
            # 2. 检查是否需要同步（避免重复同步）
            dao = MoneyFlowDAO(session)
            if dao.is_data_exists(last_trading_day):
                logger.info(f"交易日 {last_trading_day} 数据已存在，跳过同步")
                return 0
            
            # 3. 获取单日数据
            trade_date_str = last_trading_day.strftime('%Y%m%d')
            logger.info(f"开始同步交易日 {trade_date_str} 的资金流向数据")
            
            daily_data = self.tushare_service.get_moneyflow_by_date(trade_date_str)
            
            if not daily_data.empty:
                # 数据预处理
                processed_data = self._preprocess_dataframe(daily_data)
                
                # 转换为字典列表
                moneyflows_data = processed_data.to_dict('records')
                
                # 批量插入到数据库
                count = dao.bulk_upsert(moneyflows_data)
                
                logger.info(f"交易日 {last_trading_day} 资金流向数据同步完成，共 {len(daily_data)} 条记录")
                return count
            else:
                logger.warning(f"交易日 {last_trading_day} 无资金流向数据")
                return 0
                
        except Exception as e:
            logger.error(f"日常资金流向数据同步失败: {e}")
            raise
    
    def sync_specific_date(self, trade_date: str, session) -> int:
        """
        同步指定交易日的数据
        
        Args:
            trade_date: 交易日期 YYYYMMDD
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info(f"开始同步指定交易日资金流向数据: {trade_date}")
            
            # 获取指定日期数据
            daily_data = self.tushare_service.get_moneyflow_by_date(trade_date)
            
            if not daily_data.empty:
                # 数据预处理
                processed_data = self._preprocess_dataframe(daily_data)
                
                # 转换为字典列表
                moneyflows_data = processed_data.to_dict('records')
                
                # 批量插入或更新到数据库
                dao = MoneyFlowDAO(session)
                count = dao.bulk_upsert(moneyflows_data)
                
                logger.info(f"交易日 {trade_date} 资金流向数据同步完成，共 {len(daily_data)} 条记录")
                return count
            else:
                logger.warning(f"交易日 {trade_date} 无资金流向数据")
                return 0
                
        except Exception as e:
            logger.error(f"同步指定交易日资金流向数据失败: {e}")
            raise
    
    def sync_today_data(self, session) -> int:
        """
        同步当日资金流向数据
        
        Args:
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            # 获取今日日期
            today = datetime.now().date()
            trade_date_str = today.strftime('%Y%m%d')
            
            logger.info(f"开始同步当日资金流向数据: {trade_date_str}")
            
            # 检查今日是否为交易日
            if not self.trade_cal_service.is_trading_day(today.strftime('%Y-%m-%d'), 'SSE', session):
                logger.warning(f"今日 {today} 不是交易日，跳过同步")
                return 0
            
            # 调用指定日期同步方法
            return self.sync_specific_date(trade_date_str, session)
                
        except Exception as e:
            logger.error(f"同步当日资金流向数据失败: {e}")
            raise
    
    def _get_trading_days_for_polling(self, start_date: str, end_date: str, session) -> List[date]:
        """
        获取需要轮询的交易日列表
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            session: 数据库会话
            
        Returns:
            交易日列表
        """
        try:
            # 转换日期格式：从 YYYYMMDD 转换为 YYYY-MM-DD
            start_date_formatted = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
            end_date_formatted = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}"
            
            # 从数据库获取交易日历
            trading_days = self.trade_cal_service.get_trading_days(
                start_date=start_date_formatted,
                end_date=end_date_formatted,
                exchange='SSE',  # 使用上交所交易日历
                session=session
            )
            
            # 转换为日期对象列表
            return [day for day in trading_days]
            
        except Exception as e:
            logger.error(f"获取交易日列表失败: {e}")
            raise
    
    def _get_last_trading_day(self, session) -> Optional[date]:
        """
        获取上一个交易日
        
        Args:
            session: 数据库会话
            
        Returns:
            上一个交易日
        """
        try:
            # 获取交易日历DAO
            trade_cal_dao = TradeCalDAO(session)
            
            # 获取当前日期
            today = datetime.now().date()
            
            # 查找上一个交易日
            from models.trade_cal import TradeCal
            last_trading_day = session.query(TradeCal.cal_date).filter(
                TradeCal.exchange == 'SSE',
                TradeCal.cal_date < today,
                TradeCal.is_open == '1'
            ).order_by(TradeCal.cal_date.desc()).first()
            
            # 简化版本：获取最近3天的交易日
            for i in range(1, 4):
                check_date = today - timedelta(days=i)
                if self.trade_cal_service.is_trading_day(check_date.strftime('%Y-%m-%d'), 'SSE', session):
                    return check_date
            
            return last_trading_day[0] if last_trading_day else None
            
        except Exception as e:
            logger.error(f"获取上一个交易日失败: {e}")
            raise
    
    def _preprocess_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        预处理DataFrame数据
        
        Args:
            df: 原始DataFrame
            
        Returns:
            处理后的DataFrame
        """
        try:
            # 复制DataFrame避免修改原始数据
            df = df.copy()
            
            # 处理日期字段
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'], format='%Y%m%d', errors='coerce').dt.date
                # 将NaT转换为None，避免MySQL报错
                df['trade_date'] = df['trade_date'].where(pd.notna(df['trade_date']), None)
            
            # 处理数值字段，将空值转换为None
            numeric_columns = [
                'buy_sm_vol', 'buy_sm_amount', 'sell_sm_vol', 'sell_sm_amount',
                'buy_md_vol', 'buy_md_amount', 'sell_md_vol', 'sell_md_amount',
                'buy_lg_vol', 'buy_lg_amount', 'sell_lg_vol', 'sell_lg_amount',
                'buy_elg_vol', 'buy_elg_amount', 'sell_elg_vol', 'sell_elg_amount',
                'net_mf_vol', 'net_mf_amount'
            ]
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].where(pd.notna(df[col]), None)
            
            # 添加时间戳
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()
            
            logger.info(f"资金流向数据预处理完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"资金流向数据预处理失败: {e}")
            raise
    
    def get_sync_progress(self, session) -> Dict[str, Any]:
        """
        获取同步进度信息
        
        Args:
            session: 数据库会话
            
        Returns:
            同步进度信息
        """
        try:
            dao = MoneyFlowDAO(session)
            trade_cal_dao = TradeCalDAO(session)
            
            # 获取统计信息
            statistics = dao.get_statistics()
            
            # 获取交易日历统计
            trade_cal_stats = trade_cal_dao.get_statistics()
            
            # 计算进度
            date_range = statistics.get('date_range', {})
            start_date = date_range.get('start_date')
            end_date = date_range.get('end_date')
            
            if start_date and end_date:
                # 获取交易日总数
                total_trading_days = trade_cal_dao.get_count()
                
                # 获取已同步的交易日数
                synced_trading_days = dao.get_count()
                
                progress = {
                    'total_records': statistics.get('total_count', 0),
                    'stock_count': statistics.get('stock_count', 0),
                    'date_range': date_range,
                    'yearly_stats': statistics.get('yearly_stats', {}),
                    'net_inflow_stats': statistics.get('net_inflow_stats', {}),
                    'last_updated': statistics.get('last_updated'),
                    'sync_progress': {
                        'total_trading_days': total_trading_days,
                        'synced_records': synced_trading_days,
                        'progress_percentage': round((synced_trading_days / total_trading_days * 100), 2) if total_trading_days > 0 else 0
                    }
                }
            else:
                progress = statistics
            
            logger.info(f"获取资金流向同步进度信息成功: {progress}")
            return progress
            
        except Exception as e:
            logger.error(f"获取资金流向同步进度信息失败: {e}")
            raise
    
    def get_top_net_inflow_stocks(self, session, trade_date: date, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取指定日期净流入额最高的股票
        
        Args:
            session: 数据库会话
            trade_date: 交易日期
            limit: 返回数量限制
            
        Returns:
            净流入额最高的股票列表
        """
        try:
            dao = MoneyFlowDAO(session)
            stocks = dao.get_top_net_inflow(trade_date, limit)
            
            return [
                {
                    'ts_code': stock.ts_code,
                    'trade_date': stock.trade_date,
                    'net_mf_amount': float(stock.net_mf_amount) if stock.net_mf_amount else 0,
                    'net_mf_vol': stock.net_mf_vol,
                    'buy_elg_amount': float(stock.buy_elg_amount) if stock.buy_elg_amount else 0,
                    'sell_elg_amount': float(stock.sell_elg_amount) if stock.sell_elg_amount else 0
                }
                for stock in stocks
            ]
        except Exception as e:
            logger.error(f"获取净流入额最高股票失败: {e}")
            raise
    
    def get_top_net_outflow_stocks(self, session, trade_date: date, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取指定日期净流出额最高的股票
        
        Args:
            session: 数据库会话
            trade_date: 交易日期
            limit: 返回数量限制
            
        Returns:
            净流出额最高的股票列表
        """
        try:
            dao = MoneyFlowDAO(session)
            stocks = dao.get_top_net_outflow(trade_date, limit)
            
            return [
                {
                    'ts_code': stock.ts_code,
                    'trade_date': stock.trade_date,
                    'net_mf_amount': float(stock.net_mf_amount) if stock.net_mf_amount else 0,
                    'net_mf_vol': stock.net_mf_vol,
                    'buy_elg_amount': float(stock.buy_elg_amount) if stock.buy_elg_amount else 0,
                    'sell_elg_amount': float(stock.sell_elg_amount) if stock.sell_elg_amount else 0
                }
                for stock in stocks
            ]
        except Exception as e:
            logger.error(f"获取净流出额最高股票失败: {e}")
            raise
