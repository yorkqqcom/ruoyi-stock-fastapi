"""
交易日历服务
"""
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
from datetime import datetime, date
from dao.trade_cal_dao import TradeCalDAO
from models.trade_cal import TradeCal
from services.tushare_service import TushareService
from config import config

class TradeCalService:
    """交易日历服务类"""
    
    def __init__(self, tushare_service: Optional[TushareService] = None):
        """
        初始化交易日历服务
        
        Args:
            tushare_service: Tushare服务实例，如果不提供则创建新实例
        """
        self.tushare_service = tushare_service or TushareService()
    
    def get_trade_cal(self, 
                     exchange: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     is_open: Optional[str] = None) -> pd.DataFrame:
        """
        获取交易日历数据
        
        Args:
            exchange: 交易所 SSE上交所,SZSE深交所,CFFEX 中金所,SHFE 上期所,CZCE 郑商所,DCE 大商所,INE 上能源
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            is_open: 是否交易 '0'休市 '1'交易
            
        Returns:
            包含交易日历信息的DataFrame
        """
        try:
            logger.info(f"开始获取交易日历数据，参数: exchange={exchange}, start_date={start_date}, end_date={end_date}")
            
            # 构建查询参数
            params = {}
            if exchange:
                params['exchange'] = exchange
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if is_open:
                params['is_open'] = is_open
            
            # 调用API
            data = self.tushare_service._handle_rate_limit(self.tushare_service.pro.trade_cal, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取交易日历数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到交易日历数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取交易日历数据失败: {e}")
            raise
    
    def sync_trade_cal(self, 
                      exchange: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None,
                      session=None) -> int:
        """
        同步交易日历数据到数据库
        
        Args:
            exchange: 交易所
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info(f"开始同步交易日历数据，参数: exchange={exchange}, start_date={start_date}, end_date={end_date}")
            
            # 获取交易日历数据
            df = self.get_trade_cal(exchange=exchange, start_date=start_date, end_date=end_date)
            
            if df.empty:
                logger.warning("未获取到交易日历数据")
                return 0
            
            # 数据预处理
            df = self._preprocess_dataframe(df)
            
            # 转换为字典列表
            trade_cals_data = df.to_dict('records')
            
            # 批量插入或更新到数据库
            dao = TradeCalDAO(session)
            count = dao.bulk_upsert(trade_cals_data)
            
            logger.info(f"同步交易日历数据完成，共处理 {count} 条记录")
            return count
            
        except Exception as e:
            logger.error(f"同步交易日历数据失败: {e}")
            raise
    
    def sync_all_exchanges_trade_cal(self, 
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None,
                                   session=None) -> int:
        """
        同步所有交易所的交易日历数据
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            logger.info("开始同步所有交易所的交易日历数据")
            
            exchanges = ['SSE', 'SZSE', 'CFFEX', 'SHFE', 'CZCE', 'DCE', 'INE']
            total_count = 0
            
            for exchange in exchanges:
                try:
                    count = self.sync_trade_cal(
                        exchange=exchange,
                        start_date=start_date,
                        end_date=end_date,
                        session=session
                    )
                    total_count += count
                    logger.info(f"{exchange} 交易所交易日历同步完成，处理 {count} 条记录")
                except Exception as e:
                    logger.error(f"{exchange} 交易所交易日历同步失败: {e}")
                    continue
            
            logger.info(f"所有交易所交易日历同步完成，共处理 {total_count} 条记录")
            return total_count
            
        except Exception as e:
            logger.error(f"同步所有交易所交易日历失败: {e}")
            raise
    
    def sync_recent_trade_cal(self, years: int = 3, session=None) -> int:
        """
        同步最近几年的交易日历数据
        
        Args:
            years: 同步最近几年的数据，默认3年
            session: 数据库会话
            
        Returns:
            同步的记录数量
        """
        try:
            from datetime import datetime, timedelta
            
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=years*365)).strftime('%Y%m%d')
            
            logger.info(f"开始同步最近{years}年的交易日历数据: {start_date} 到 {end_date}")
            
            return self.sync_all_exchanges_trade_cal(
                start_date=start_date,
                end_date=end_date,
                session=session
            )
            
        except Exception as e:
            logger.error(f"同步最近交易日历失败: {e}")
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
            if 'cal_date' in df.columns:
                df['cal_date'] = pd.to_datetime(df['cal_date'], format='%Y%m%d', errors='coerce').dt.date
            
            if 'pretrade_date' in df.columns:
                df['pretrade_date'] = pd.to_datetime(df['pretrade_date'], format='%Y%m%d', errors='coerce').dt.date
                # 将NaT转换为None
                df['pretrade_date'] = df['pretrade_date'].where(pd.notna(df['pretrade_date']), None)
            
            # 处理空值
            df = df.fillna('')
            
            # 确保字符串字段不为None
            string_columns = ['exchange', 'is_open']
            for col in string_columns:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '')
            
            # 添加时间戳
            df['created_at'] = datetime.now()
            df['updated_at'] = datetime.now()
            
            logger.info(f"交易日历数据预处理完成，共 {len(df)} 条记录")
            return df
            
        except Exception as e:
            logger.error(f"交易日历数据预处理失败: {e}")
            raise
    
    def get_trade_cal_statistics(self, session) -> Dict[str, Any]:
        """
        获取交易日历统计信息
        
        Args:
            session: 数据库会话
            
        Returns:
            统计信息字典
        """
        try:
            dao = TradeCalDAO(session)
            statistics = dao.get_statistics()
            
            logger.info(f"获取交易日历统计信息成功: {statistics}")
            return statistics
            
        except Exception as e:
            logger.error(f"获取交易日历统计信息失败: {e}")
            raise
    
    def get_trading_days(self, 
                        start_date: str, 
                        end_date: str, 
                        exchange: Optional[str] = None,
                        session=None) -> List[date]:
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期 YYYY-MM-DD
            end_date: 结束日期 YYYY-MM-DD
            exchange: 交易所
            session: 数据库会话
            
        Returns:
            交易日列表
        """
        try:
            from datetime import datetime
            
            # 转换日期格式
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            dao = TradeCalDAO(session)
            trading_days = dao.get_trading_days(start_dt, end_dt, exchange)
            
            return [day.cal_date for day in trading_days]
            
        except Exception as e:
            logger.error(f"获取交易日列表失败: {e}")
            raise
    
    def is_trading_day(self, date_str: str, exchange: str = 'SSE', session=None) -> bool:
        """
        判断指定日期是否为交易日
        
        Args:
            date_str: 日期字符串 YYYY-MM-DD
            exchange: 交易所
            session: 数据库会话
            
        Returns:
            是否为交易日
        """
        try:
            from datetime import datetime
            
            cal_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            dao = TradeCalDAO(session)
            trade_cal = dao.session.query(TradeCal).filter(
                TradeCal.exchange == exchange,
                TradeCal.cal_date == cal_date
            ).first()
            
            if trade_cal:
                return trade_cal.is_open == '1'
            else:
                # 如果没有数据，使用默认判断（周末为非交易日）
                return cal_date.weekday() < 5  # 周一到周五
                
        except Exception as e:
            logger.error(f"判断交易日失败: {e}")
            return False
