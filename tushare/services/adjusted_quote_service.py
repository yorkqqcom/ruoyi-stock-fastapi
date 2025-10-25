"""
A股复权行情服务
"""
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, date, timedelta
from dao.adjusted_quote_dao import AdjustedQuoteDAO
from dao.stock_basic_dao import StockBasicDAO
from dao.trade_cal_dao import TradeCalDAO
from services.tushare_service import TushareService
from services.trade_cal_service import TradeCalService
from config import config
import time

class AdjustedQuoteService:
    """A股复权行情服务类"""
    
    def __init__(self, tushare_service: Optional[TushareService] = None, 
                 trade_cal_service: Optional[TradeCalService] = None):
        """
        初始化复权行情服务
        
        Args:
            tushare_service: Tushare服务实例，如果不提供则创建新实例
            trade_cal_service: 交易日历服务实例，如果不提供则创建新实例
        """
        self.tushare_service = tushare_service or TushareService()
        self.trade_cal_service = trade_cal_service or TradeCalService()
    
    def _get_last_trading_day(self, session) -> Optional[date]:
        """
        获取上一个交易日（基于交易日历）
        
        Args:
            session: 数据库会话
            
        Returns:
            上一个交易日日期，若不存在返回None
        """
        try:
            today = datetime.now().date()
            start_date = today - timedelta(days=10)
            trade_cal_dao = TradeCalDAO(session)
            trading_days = trade_cal_dao.get_trading_days(start_date=start_date, end_date=today - timedelta(days=1), exchange='SSE')
            if not trading_days:
                return None
            # TradeCalDAO 返回的是 TradeCal 实体列表，取最后一个日期
            return trading_days[-1].cal_date
        except Exception as e:
            logger.error(f"获取上一个交易日失败: {e}")
            raise
    
    def sync_historical_data_by_stock(self, session, ts_code: str, start_date: str = '20140101', 
                                    end_date: str = None, adj_types: List[str] = None) -> int:
        """
        按股票同步历史复权行情数据
        
        Args:
            session: 数据库会话
            ts_code: 股票代码
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD，默认为当前日期
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            logger.info(f"开始同步股票 {ts_code} 的历史复权行情数据: {start_date} 到 {end_date}")
            
            dao = AdjustedQuoteDAO(session)
            total_count = 0
            
            # 按复权类型逐个获取数据
            for adj_type in adj_types:
                try:
                    logger.info(f"正在获取 {ts_code} 的 {adj_type or 'none'} 复权数据")
                    
                    # 获取复权行情数据
                    data = self.tushare_service.get_pro_bar(
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        adj=adj_type
                    )
                    
                    if not data.empty:
                        # 数据预处理
                        processed_data = self._preprocess_dataframe(data, adj_type)
                        
                        # 转换为字典列表
                        quotes_data = processed_data.to_dict('records')
                        
                        # 批量插入到数据库
                        count = dao.bulk_upsert(quotes_data)
                        total_count += count
                        
                        logger.info(f"股票 {ts_code} 的 {adj_type or 'none'} 复权数据同步完成，共 {len(data)} 条记录")
                    else:
                        logger.warning(f"股票 {ts_code} 的 {adj_type or 'none'} 复权数据为空")
                    
                    # 控制API调用频率
                    time.sleep(0.3)  # 200次/分钟，每次间隔0.3秒
                    
                except Exception as e:
                    logger.error(f"获取股票 {ts_code} 的 {adj_type or 'none'} 复权数据失败: {e}")
                    continue
            
            logger.info(f"股票 {ts_code} 历史复权行情数据同步完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"同步股票 {ts_code} 历史复权行情数据失败: {e}")
            raise
    
    def sync_historical_data_batch(self, session, ts_codes: List[str], start_date: str = '20140101', 
                                 end_date: str = None, adj_types: List[str] = None) -> int:
        """
        批量同步历史复权行情数据
        
        Args:
            session: 数据库会话
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD，默认为当前日期
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            logger.info(f"开始批量同步历史复权行情数据: {len(ts_codes)} 只股票，{start_date} 到 {end_date}")
            
            total_count = 0
            success_count = 0
            failed_count = 0
            
            for i, ts_code in enumerate(ts_codes, 1):
                try:
                    logger.info(f"正在同步第 {i}/{len(ts_codes)} 只股票: {ts_code}")
                    
                    count = self.sync_historical_data_by_stock(
                        session=session,
                        ts_code=ts_code,
                        start_date=start_date,
                        end_date=end_date,
                        adj_types=adj_types
                    )
                    
                    total_count += count
                    success_count += 1
                    
                    logger.info(f"股票 {ts_code} 同步完成，共 {count} 条记录")
                    
                except Exception as e:
                    logger.error(f"股票 {ts_code} 同步失败: {e}")
                    failed_count += 1
                    continue
            
            logger.info(f"批量同步完成，成功 {success_count} 只，失败 {failed_count} 只，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"批量同步历史复权行情数据失败: {e}")
            raise
    
    def sync_daily_data(self, session, trade_date: str, adj_types: List[str] = None) -> int:
        """
        同步指定交易日的复权行情数据
        
        Args:
            session: 数据库会话
            trade_date: 交易日期 YYYYMMDD
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            logger.info(f"开始同步交易日 {trade_date} 的复权行情数据")
            
            # 获取所有股票列表
            stock_basic_dao = StockBasicDAO(session)
            stocks = stock_basic_dao.get_all()
            
            if not stocks:
                logger.warning("未找到股票列表，请先同步股票基础信息")
                return 0
            
            ts_codes = [stock.ts_code for stock in stocks]
            logger.info(f"找到 {len(ts_codes)} 只股票，开始同步")
            
            dao = AdjustedQuoteDAO(session)
            total_count = 0
            
            for ts_code in ts_codes:
                try:
                    # 按复权类型获取数据
                    for adj_type in adj_types:
                        # 检查数据是否已存在
                        if dao.is_data_exists(ts_code, datetime.strptime(trade_date, '%Y%m%d').date(), adj_type):
                            continue
                        
                        # 获取单日数据
                        data = self.tushare_service.get_pro_bar(
                            ts_code=ts_code,
                            start_date=trade_date,
                            end_date=trade_date,
                            adj=adj_type
                        )
                        
                        if not data.empty:
                            # 数据预处理
                            processed_data = self._preprocess_dataframe(data, adj_type)
                            
                            # 转换为字典列表
                            quotes_data = processed_data.to_dict('records')
                            
                            # 批量插入到数据库
                            count = dao.bulk_upsert(quotes_data)
                            total_count += count
                        
                        # 控制API调用频率
                        time.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"同步股票 {ts_code} 的交易日 {trade_date} 数据失败: {e}")
                    continue
            
            logger.info(f"交易日 {trade_date} 复权行情数据同步完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"同步交易日 {trade_date} 复权行情数据失败: {e}")
            raise
    
    def sync_today_data(self, session, adj_types: List[str] = None) -> int:
        """
        同步当日复权行情数据
        
        Args:
            session: 数据库会话
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            # 获取今日日期
            today = datetime.now().date()
            trade_date_str = today.strftime('%Y%m%d')
            
            logger.info(f"开始同步当日复权行情数据: {trade_date_str}")
            
            # 检查今日是否为交易日
            if not self.trade_cal_service.is_trading_day(today.strftime('%Y-%m-%d'), 'SSE', session):
                logger.warning(f"今日 {today} 不是交易日，跳过同步")
                return 0
            
            # 调用指定日期同步方法
            return self.sync_daily_data(session, trade_date_str, adj_types)
                
        except Exception as e:
            logger.error(f"同步当日复权行情数据失败: {e}")
            raise
    
    def sync_daily_data_optimized(self, session, adj_types: List[str] = None) -> int:
        """
        优化的日常复权数据同步（自动定位上一个交易日，并避免重复）
        
        Args:
            session: 数据库会话
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            logger.info("开始日常复权行情数据同步")
            last_trading_day = self._get_last_trading_day(session)
            if not last_trading_day:
                logger.warning("未找到上一个交易日")
                return 0
            
            logger.info(f"上一个交易日: {last_trading_day}")
            trade_date_str = last_trading_day.strftime('%Y%m%d')
            
            # 获取所有股票列表
            stock_basic_dao = StockBasicDAO(session)
            stocks = stock_basic_dao.get_all()
            if not stocks:
                logger.warning("未找到股票列表，请先同步股票基础信息")
                return 0
            ts_codes = [stock.ts_code for stock in stocks]
            
            dao = AdjustedQuoteDAO(session)
            total_count = 0
            
            for ts_code in ts_codes:
                try:
                    for adj_type in adj_types:
                        # 已有数据则跳过，避免重复
                        if dao.is_data_exists(ts_code, last_trading_day, adj_type):
                            continue
                        
                        data = self.tushare_service.get_pro_bar(
                            ts_code=ts_code,
                            start_date=trade_date_str,
                            end_date=trade_date_str,
                            adj=adj_type
                        )
                        
                        if not data.empty:
                            processed_data = self._preprocess_dataframe(data, adj_type)
                            quotes_data = processed_data.to_dict('records')
                            count = dao.bulk_upsert(quotes_data)
                            total_count += count
                        
                        time.sleep(0.3)
                except Exception as e:
                    logger.error(f"同步股票 {ts_code} 的交易日 {trade_date_str} 数据失败: {e}")
                    continue
            
            logger.info(f"交易日 {trade_date_str} 复权行情数据同步完成，共处理 {total_count} 条记录")
            return total_count
        except Exception as e:
            logger.error(f"日常复权行情数据同步失败: {e}")
            raise
    
    def sync_missing_data(self, session, start_date: str = '20140101', end_date: str = None, 
                         adj_types: List[str] = None) -> int:
        """
        同步缺失的复权行情数据
        
        Args:
            session: 数据库会话
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD，默认为当前日期
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步的记录数量
        """
        try:
            if end_date is None:
                end_date = datetime.now().strftime('%Y%m%d')
            
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            logger.info(f"开始同步缺失的复权行情数据: {start_date} 到 {end_date}")
            
            # 获取所有股票列表
            stock_basic_dao = StockBasicDAO(session)
            stocks = stock_basic_dao.get_all()
            
            if not stocks:
                logger.warning("未找到股票列表，请先同步股票基础信息")
                return 0
            
            ts_codes = [stock.ts_code for stock in stocks]
            
            # 获取缺失的数据列表
            dao = AdjustedQuoteDAO(session)
            missing_data = dao.get_missing_data(
                ts_codes=ts_codes,
                start_date=datetime.strptime(start_date, '%Y%m%d').date(),
                end_date=datetime.strptime(end_date, '%Y%m%d').date(),
                adj_types=adj_types
            )
            
            if not missing_data:
                logger.info("未发现缺失数据")
                return 0
            
            logger.info(f"发现 {len(missing_data)} 个缺失的数据项，开始同步")
            
            total_count = 0
            for i, missing_item in enumerate(missing_data, 1):
                try:
                    ts_code = missing_item['ts_code']
                    adj_type = missing_item['adj_type']
                    start_date_obj = missing_item['start_date']
                    end_date_obj = missing_item['end_date']
                    
                    logger.info(f"正在同步第 {i}/{len(missing_data)} 个缺失项: {ts_code} - {adj_type}")
                    
                    # 获取数据
                    data = self.tushare_service.get_pro_bar(
                        ts_code=ts_code,
                        start_date=start_date_obj.strftime('%Y%m%d'),
                        end_date=end_date_obj.strftime('%Y%m%d'),
                        adj=adj_type
                    )
                    
                    if not data.empty:
                        # 数据预处理
                        processed_data = self._preprocess_dataframe(data, adj_type)
                        
                        # 转换为字典列表
                        quotes_data = processed_data.to_dict('records')
                        
                        # 批量插入到数据库
                        count = dao.bulk_upsert(quotes_data)
                        total_count += count
                        
                        logger.info(f"缺失项 {ts_code} - {adj_type} 同步完成，共 {count} 条记录")
                    
                    # 控制API调用频率
                    time.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"同步缺失项失败: {e}")
                    continue
            
            logger.info(f"缺失数据同步完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"同步缺失复权行情数据失败: {e}")
            raise
    
    def _preprocess_dataframe(self, df: pd.DataFrame, adj_type: str) -> pd.DataFrame:
        """
        预处理DataFrame数据
        
        Args:
            df: 原始DataFrame
            adj_type: 复权类型
            
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
            numeric_columns = ['open', 'high', 'low', 'close', 'pre_close', 'change', 'pct_chg', 'vol', 'amount']
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].where(pd.notna(df[col]), None)
            
            # 重命名change字段为change_amount（避免与Python关键字冲突）
            if 'change' in df.columns:
                df = df.rename(columns={'change': 'change_amount'})
            
            # 添加复权类型字段
            df['adj_type'] = adj_type or 'none'
            
            # 添加时间戳
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()
            
            logger.info(f"复权行情数据预处理完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"复权行情数据预处理失败: {e}")
            raise
    
    def get_sync_progress(self, session, adj_types: List[str] = None) -> Dict[str, Any]:
        """
        获取同步进度信息
        
        Args:
            session: 数据库会话
            adj_types: 复权类型列表，默认为 ['qfq', 'hfq', None]
            
        Returns:
            同步进度信息
        """
        try:
            if adj_types is None:
                adj_types = ['qfq', 'hfq', None]
            
            dao = AdjustedQuoteDAO(session)
            
            # 获取统计信息
            statistics = dao.get_statistics()
            
            # 获取各复权类型的进度
            progress = dao.get_sync_progress(adj_types)
            
            result = {
                'total_statistics': statistics,
                'adj_type_progress': progress,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取复权行情同步进度信息成功: {result}")
            return result
            
        except Exception as e:
            logger.error(f"获取复权行情同步进度信息失败: {e}")
            raise
