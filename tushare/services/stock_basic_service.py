"""
股票基础信息服务
"""
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, date
from dao.stock_basic_dao import StockBasicDAO
from services.tushare_service import TushareService
from config import config

class StockBasicService:
    """股票基础信息服务类"""
    
    def __init__(self, tushare_service: Optional[TushareService] = None):
        """
        初始化股票基础信息服务
        
        Args:
            tushare_service: Tushare服务实例，如果不提供则创建新实例
        """
        self.tushare_service = tushare_service or TushareService()
    
    def sync_all_stock_basic(self, session) -> int:
        """
        同步所有股票基础信息到数据库
        
        Args:
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info("开始同步所有股票基础信息")
            
            # 获取所有股票基础信息
            df = self.tushare_service.get_all_stock_basic()
            
            if df.empty:
                logger.warning("未获取到股票基础信息数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            stocks_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = StockBasicDAO(session)
            count = dao.bulk_upsert(stocks_data)
            
            logger.info(f"同步股票基础信息完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步股票基础信息失败: {e}")
            raise
    
    def sync_stock_basic_by_exchange(self, exchange: str, session) -> int:
        """
        根据交易所同步股票基础信息
        
        Args:
            exchange: 交易所代码 (SSE/SZSE/BSE)
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info(f"开始同步 {exchange} 交易所股票基础信息")
            
            # 获取指定交易所股票基础信息
            df = self.tushare_service.get_stock_basic_by_exchange(exchange)
            
            if df.empty:
                logger.warning(f"未获取到 {exchange} 交易所股票基础信息数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            stocks_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = StockBasicDAO(session)
            count = dao.bulk_upsert(stocks_data)
            
            logger.info(f"同步 {exchange} 交易所股票基础信息完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步 {exchange} 交易所股票基础信息失败: {e}")
            raise
    
    def sync_stock_basic_by_market(self, market: str, session) -> int:
        """
        根据市场类型同步股票基础信息
        
        Args:
            market: 市场类型 (主板/创业板/科创板/CDR/北交所)
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info(f"开始同步 {market} 市场股票基础信息")
            
            # 获取指定市场股票基础信息
            df = self.tushare_service.get_stock_basic_by_market(market)
            
            if df.empty:
                logger.warning(f"未获取到 {market} 市场股票基础信息数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            stocks_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = StockBasicDAO(session)
            count = dao.bulk_upsert(stocks_data)
            
            logger.info(f"同步 {market} 市场股票基础信息完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步 {market} 市场股票基础信息失败: {e}")
            raise
    
    def sync_delisted_stocks(self, session) -> int:
        """
        同步已退市股票信息
        
        Args:
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info("开始同步已退市股票信息")
            
            # 获取已退市股票信息
            df = self.tushare_service.get_delisted_stocks()
            
            if df.empty:
                logger.warning("未获取到已退市股票信息数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            stocks_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = StockBasicDAO(session)
            count = dao.bulk_upsert(stocks_data)
            
            logger.info(f"同步已退市股票信息完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步已退市股票信息失败: {e}")
            raise
    
    def sync_suspended_stocks(self, session) -> int:
        """
        同步暂停上市股票信息
        
        Args:
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info("开始同步暂停上市股票信息")
            
            # 获取暂停上市股票信息
            df = self.tushare_service.get_suspended_stocks()
            
            if df.empty:
                logger.warning("未获取到暂停上市股票信息数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            stocks_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = StockBasicDAO(session)
            count = dao.bulk_upsert(stocks_data)
            
            logger.info(f"同步暂停上市股票信息完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步暂停上市股票信息失败: {e}")
            raise
    
    def update_stock_status(self, session) -> int:
        """
        更新股票状态（包括新增上市、退市、暂停上市等）
        
        Args:
            session: 数据库会话
            
        Returns:
            更新的记录数量
        """
        try:
            logger.info("开始更新股票状态")
            
            total_count = 0
            
            # 同步正常上市股票
            count = self.sync_all_stock_basic(session)
            total_count += count
            
            # 同步已退市股票
            count = self.sync_delisted_stocks(session)
            total_count += count
            
            # 同步暂停上市股票
            count = self.sync_suspended_stocks(session)
            total_count += count
            
            logger.info(f"更新股票状态完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"更新股票状态失败: {e}")
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
            date_columns = ['list_date', 'delist_date']
            for col in date_columns:
                if col in df.columns:
                    # 将日期字符串转换为日期对象
                    df[col] = pd.to_datetime(df[col], format='%Y%m%d', errors='coerce').dt.date
                    # 将NaT/NaN统一转换为None，避免数据库错误
                    df[col] = df[col].astype('object').where(pd.notna(df[col]), None)
            
            # 处理空值
            df = df.fillna('')
            
            # 再次确保日期列不含NaT/NaN/空字符串，统一为None
            for col in date_columns:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: x if (x is not None and x != '' and pd.notna(x)) else None)
            
            # 确保字符串字段不为None
            string_columns = ['ts_code', 'symbol', 'name', 'area', 'industry', 'fullname', 
                            'enname', 'cnspell', 'market', 'exchange', 'curr_type', 
                            'list_status', 'is_hs', 'act_name', 'act_ent_type']
            
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '')
            
            logger.info(f"数据预处理完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"数据预处理失败: {e}")
            raise
    
    def get_stock_statistics(self, session) -> Dict[str, Any]:
        """
        获取股票统计信息
        
        Args:
            session: 数据库会话
            
        Returns:
            统计信息字典
        """
        try:
            dao = StockBasicDAO(session)
            
            # 获取各种统计信息
            total_count = dao.get_count()
            active_stocks = dao.get_active_stocks()
            active_count = len(active_stocks)
            
            # 按交易所统计
            exchange_stats = {}
            for exchange in ['SSE', 'SZSE', 'BSE']:
                stocks = dao.get_by_exchange(exchange)
                exchange_stats[exchange] = len(stocks)
            
            # 按市场类型统计
            market_stats = {}
            markets = ['主板', '创业板', '科创板', 'CDR', '北交所']
            for market in markets:
                stocks = dao.get_by_market(market)
                market_stats[market] = len(stocks)
            
            statistics = {
                'total_count': total_count,
                'active_count': active_count,
                'delisted_count': total_count - active_count,
                'exchange_stats': exchange_stats,
                'market_stats': market_stats,
                'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            logger.info(f"获取股票统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取股票统计信息失败: {e}")
            raise
