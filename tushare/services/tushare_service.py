"""
Tushare数据服务基类
"""
import tushare as ts
import pandas as pd
from typing import Dict, Any, Optional, List
from loguru import logger
import time
from config import config

class TushareService:
    """Tushare数据服务基类"""
    
    def __init__(self, token: Optional[str] = None):
        """
        初始化Tushare服务
        
        Args:
            token: Tushare token，如果不提供则从配置文件读取
        """
        self.token = token or config.TUSHARE_TOKEN
        if not self.token:
            raise ValueError("Tushare token 未配置")
        
        # 设置Tushare token
        ts.set_token(self.token)
        self.pro = ts.pro_api()
        
        logger.info("Tushare服务初始化成功")
    
    def _handle_rate_limit(self, func, *args, **kwargs):
        """
        处理API频率限制
        
        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数
            
        Returns:
            函数执行结果
        """
        max_retry = config.MAX_RETRY
        retry_delay = config.RETRY_DELAY
        
        for attempt in range(max_retry):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_msg = str(e)
                if "每分钟最多访问" in error_msg or "访问过于频繁" in error_msg:
                    if attempt < max_retry - 1:
                        logger.warning(f"API访问频率限制，等待 {retry_delay} 秒后重试 (第 {attempt + 1} 次)")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"API访问频率限制，重试 {max_retry} 次后仍然失败")
                        raise
                else:
                    logger.error(f"调用Tushare API失败: {e}")
                    raise
        
        return None
    
    def get_stock_basic(self, 
                       ts_code: Optional[str] = None,
                       name: Optional[str] = None,
                       market: Optional[str] = None,
                       list_status: str = 'L',
                       exchange: Optional[str] = None,
                       is_hs: Optional[str] = None,
                       fields: Optional[str] = None) -> pd.DataFrame:
        """
        获取股票基础信息数据
        
        Args:
            ts_code: TS股票代码
            name: 名称
            market: 市场类别 （主板/创业板/科创板/CDR/北交所）
            list_status: 上市状态 L上市 D退市 P暂停上市，默认是L
            exchange: 交易所 SSE上交所 SZSE深交所 BSE北交所
            is_hs: 是否沪深港通标的，N否 H沪股通 S深股通
            fields: 返回字段，用逗号分隔
            
        Returns:
            包含股票基础信息的DataFrame
        """
        try:
            logger.info(f"开始获取股票基础信息数据，参数: ts_code={ts_code}, market={market}, list_status={list_status}")
            
            # 构建查询参数
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if name:
                params['name'] = name
            if market:
                params['market'] = market
            if list_status:
                params['list_status'] = list_status
            if exchange:
                params['exchange'] = exchange
            if is_hs:
                params['is_hs'] = is_hs
            if fields:
                params['fields'] = fields
            
            # 调用API
            data = self._handle_rate_limit(self.pro.stock_basic, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取股票基础信息数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到股票基础信息数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取股票基础信息数据失败: {e}")
            raise
    
    def get_all_stock_basic(self) -> pd.DataFrame:
        """
        获取所有股票基础信息数据
        
        Returns:
            包含所有股票基础信息的DataFrame
        """
        return self.get_stock_basic(
            exchange='',
            list_status='L',
            fields='ts_code,symbol,name,area,industry,fullname,enname,cnspell,market,exchange,curr_type,list_status,list_date,delist_date,is_hs,act_name,act_ent_type'
        )
    
    def get_stock_basic_by_exchange(self, exchange: str) -> pd.DataFrame:
        """
        根据交易所获取股票基础信息
        
        Args:
            exchange: 交易所代码 (SSE/SZSE/BSE)
            
        Returns:
            包含指定交易所股票基础信息的DataFrame
        """
        return self.get_stock_basic(
            exchange=exchange,
            list_status='L'
        )
    
    def get_stock_basic_by_market(self, market: str) -> pd.DataFrame:
        """
        根据市场类型获取股票基础信息
        
        Args:
            market: 市场类型 (主板/创业板/科创板/CDR/北交所)
            
        Returns:
            包含指定市场股票基础信息的DataFrame
        """
        return self.get_stock_basic(
            market=market,
            list_status='L'
        )
    
    def get_delisted_stocks(self) -> pd.DataFrame:
        """
        获取已退市股票信息
        
        Returns:
            包含已退市股票信息的DataFrame
        """
        return self.get_stock_basic(
            list_status='D'
        )
    
    def get_suspended_stocks(self) -> pd.DataFrame:
        """
        获取暂停上市股票信息
        
        Returns:
            包含暂停上市股票信息的DataFrame
        """
        return self.get_stock_basic(
            list_status='P'
        )
    
    def get_daily(self, 
                  ts_code: Optional[str] = None,
                  trade_date: Optional[str] = None,
                  start_date: Optional[str] = None,
                  end_date: Optional[str] = None,
                  fields: Optional[str] = None) -> pd.DataFrame:
        """
        获取A股日线行情数据
        
        Args:
            ts_code: 股票代码（支持多个股票同时提取，逗号分隔）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            fields: 返回字段，用逗号分隔
            
        Returns:
            包含日线行情数据的DataFrame
        """
        try:
            logger.info(f"开始获取A股日线行情数据，参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")
            
            # 构建查询参数
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if fields:
                params['fields'] = fields
            
            # 调用API
            data = self._handle_rate_limit(self.pro.daily, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取A股日线行情数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到A股日线行情数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取A股日线行情数据失败: {e}")
            raise
    
    def get_daily_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        根据交易日期获取所有股票的日线行情数据
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
            
        Returns:
            包含指定日期所有股票日线行情数据的DataFrame
        """
        return self.get_daily(trade_date=trade_date)
    
    def get_daily_by_stock(self, ts_code: str, start_date: Optional[str] = None, 
                          end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据股票代码获取日线行情数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含指定股票日线行情数据的DataFrame
        """
        return self.get_daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_daily_by_stocks(self, ts_codes: List[str], start_date: Optional[str] = None, 
                           end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据多个股票代码获取日线行情数据
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含多个股票日线行情数据的DataFrame
        """
        ts_code_str = ','.join(ts_codes)
        return self.get_daily(ts_code=ts_code_str, start_date=start_date, end_date=end_date)
    
    def get_moneyflow(self, 
                     ts_code: Optional[str] = None,
                     trade_date: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     fields: Optional[str] = None) -> pd.DataFrame:
        """
        获取个股资金流向数据
        
        Args:
            ts_code: 股票代码（支持多个股票同时提取，逗号分隔）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            fields: 返回字段，用逗号分隔
            
        Returns:
            包含资金流向数据的DataFrame
        """
        try:
            logger.info(f"开始获取个股资金流向数据，参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")
            
            # 构建查询参数
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if fields:
                params['fields'] = fields
            
            # 调用API
            data = self._handle_rate_limit(self.pro.moneyflow, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取个股资金流向数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到个股资金流向数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取个股资金流向数据失败: {e}")
            raise
    
    def get_moneyflow_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        根据交易日期获取所有股票的资金流向数据
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
            
        Returns:
            包含指定日期所有股票资金流向数据的DataFrame
        """
        return self.get_moneyflow(trade_date=trade_date)
    
    def get_moneyflow_by_stock(self, ts_code: str, start_date: Optional[str] = None, 
                              end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据股票代码获取资金流向数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含指定股票资金流向数据的DataFrame
        """
        return self.get_moneyflow(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_moneyflow_by_stocks(self, ts_codes: List[str], start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据多个股票代码获取资金流向数据
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含多个股票资金流向数据的DataFrame
        """
        ts_code_str = ','.join(ts_codes)
        return self.get_moneyflow(ts_code=ts_code_str, start_date=start_date, end_date=end_date)
    
    def get_pro_bar(self, 
                   ts_code: str,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   asset: str = 'E',
                   adj: Optional[str] = None,
                   freq: str = 'D',
                   ma: Optional[List[int]] = None) -> pd.DataFrame:
        """
        获取复权行情数据（通用行情接口）
        
        Args:
            ts_code: 证券代码
            start_date: 开始日期 (格式：YYYYMMDD)
            end_date: 结束日期 (格式：YYYYMMDD)
            asset: 资产类别：E股票 I沪深指数 C数字货币 FT期货 FD基金 O期权，默认E
            adj: 复权类型(只针对股票)：None未复权 qfq前复权 hfq后复权，默认None
            freq: 数据频度：1MIN表示1分钟（1/5/15/30/60分钟） D日线，默认D
            ma: 均线，支持任意周期的均价和均量，输入任意合理int数值
            
        Returns:
            包含复权行情数据的DataFrame
        """
        try:
            logger.info(f"开始获取复权行情数据，参数: ts_code={ts_code}, start_date={start_date}, end_date={end_date}, adj={adj}")
            
            # 构建查询参数
            params = {
                'ts_code': ts_code,
                'asset': asset,
                'freq': freq
            }
            
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            if adj:
                params['adj'] = adj
            if ma:
                params['ma'] = ma
            
            # 调用API - pro_bar是ts模块的直接方法，不是pro对象的方法
            import tushare as ts
            data = self._handle_rate_limit(ts.pro_bar, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取复权行情数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到复权行情数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取复权行情数据失败: {e}")
            raise
    
    def get_pro_bar_by_stock(self, ts_code: str, start_date: Optional[str] = None, 
                           end_date: Optional[str] = None, adj: Optional[str] = None) -> pd.DataFrame:
        """
        根据股票代码获取复权行情数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            adj: 复权类型 None/qfq/hfq
            
        Returns:
            包含指定股票复权行情数据的DataFrame
        """
        return self.get_pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj=adj)
    
    def get_pro_bar_multiple_adj(self, ts_code: str, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None, adj_types: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        获取多种复权类型的数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            adj_types: 复权类型列表，如 ['qfq', 'hfq', None]
            
        Returns:
            包含不同复权类型数据的字典
        """
        if adj_types is None:
            adj_types = ['qfq', 'hfq', None]
        
        results = {}
        for adj_type in adj_types:
            try:
                data = self.get_pro_bar(ts_code=ts_code, start_date=start_date, end_date=end_date, adj=adj_type)
                results[adj_type or 'none'] = data
                logger.info(f"获取 {ts_code} 的 {adj_type or 'none'} 复权数据成功，共 {len(data)} 条记录")
            except Exception as e:
                logger.error(f"获取 {ts_code} 的 {adj_type or 'none'} 复权数据失败: {e}")
                results[adj_type or 'none'] = pd.DataFrame()
        
        return results
    
    def get_adj_factor(self, 
                      ts_code: Optional[str] = None,
                      trade_date: Optional[str] = None,
                      start_date: Optional[str] = None,
                      end_date: Optional[str] = None) -> pd.DataFrame:
        """
        获取复权因子数据
        
        Args:
            ts_code: 股票代码（支持多个股票同时提取，逗号分隔）
            trade_date: 交易日期（YYYYMMDD）
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含复权因子数据的DataFrame
        """
        try:
            logger.info(f"开始获取复权因子数据，参数: ts_code={ts_code}, trade_date={trade_date}, start_date={start_date}, end_date={end_date}")
            
            # 构建查询参数
            params = {}
            if ts_code:
                params['ts_code'] = ts_code
            if trade_date:
                params['trade_date'] = trade_date
            if start_date:
                params['start_date'] = start_date
            if end_date:
                params['end_date'] = end_date
            
            # 调用API
            data = self._handle_rate_limit(self.pro.adj_factor, **params)
            
            if data is not None and not data.empty:
                logger.info(f"成功获取复权因子数据，共 {len(data)} 条记录")
                return data
            else:
                logger.warning("未获取到复权因子数据")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取复权因子数据失败: {e}")
            raise
    
    def get_adj_factor_by_date(self, trade_date: str) -> pd.DataFrame:
        """
        根据交易日期获取所有股票的复权因子
        
        Args:
            trade_date: 交易日期（YYYYMMDD）
            
        Returns:
            包含指定日期所有股票复权因子的DataFrame
        """
        return self.get_adj_factor(trade_date=trade_date)
    
    def get_adj_factor_by_stock(self, ts_code: str, start_date: Optional[str] = None, 
                               end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据股票代码获取复权因子数据
        
        Args:
            ts_code: 股票代码
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含指定股票复权因子数据的DataFrame
        """
        return self.get_adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
    
    def get_adj_factor_by_stocks(self, ts_codes: List[str], start_date: Optional[str] = None, 
                                end_date: Optional[str] = None) -> pd.DataFrame:
        """
        根据多个股票代码获取复权因子数据
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期(YYYYMMDD)
            end_date: 结束日期(YYYYMMDD)
            
        Returns:
            包含多个股票复权因子数据的DataFrame
        """
        ts_code_str = ','.join(ts_codes)
        return self.get_adj_factor(ts_code=ts_code_str, start_date=start_date, end_date=end_date)