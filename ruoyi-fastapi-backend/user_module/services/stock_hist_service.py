from sqlalchemy import between
from datetime import date, datetime
import akshare as ak
from functools import lru_cache
import pandas as pd
import numpy as np
from scipy.stats import norm
from typing import Dict, List, Tuple
FIELD_MAPPING = {
    "stock_zh_a_spot_em": {
        '代码': 'symbol',
        '名称': 'name',
        '最新价': 'price',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amt',
        '成交量': 'volume',
        '成交额': 'turnover',
        '振幅': 'amplitude',
        '最高': 'high',
        '最低': 'low',
        '今开': 'open',
        '昨收': 'pre_close',
        '量比': 'volume_ratio',
        '换手率': 'turnover_rate',
        '市盈率-动态': 'pe_ratio',
        '市净率': 'pb_ratio',
        '总市值': 'total_market_cap',
        '流通市值': 'circ_market_cap'
    },
    "stock_zh_a_hist": {
        '日期': 'date',
        '股票代码': 'symbol',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude_pct',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amt',
        '换手率': 'turnover_rate'
    },
    "stock_fund_flow_individual": {
        '序号': 'rank',
        '股票代码': 'symbol',
        '股票简称': 'name',
        '最新价': 'price',
        '涨跌幅': 'change_pct',
        '换手率': 'turnover_rate',
        '流入资金': 'inflow',
        '流出资金': 'outflow',
        '净额': 'net_amount',
        '成交额': 'amount'
    }
}
class StockHistService:
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_cached_stock_list(cache_key: str) -> pd.DataFrame:
        df = ak.stock_fund_flow_individual(symbol="即时")
        df = df.rename(columns=FIELD_MAPPING["stock_fund_flow_individual"])
        # 确保股票代码是字符串格式
        df['symbol'] = df['symbol'].astype(str).str.zfill(6)
        
        # 去重处理：按股票代码去重，保留第一个出现的记录
        df = df.drop_duplicates(subset=['symbol'], keep='first')
        
        return df

    @staticmethod
    async def get_stock_list():
        # 使用当前日期作为缓存键
        cache_key = datetime.now().strftime('%Y-%m-%d')
        df = StockHistService._get_cached_stock_list(cache_key)
        # 确保返回的DataFrame中的股票代码是字符串格式
        df['symbol'] = df['symbol'].astype(str).str.zfill(6)
        return df

    @staticmethod
    async def get_stock_spot_em(cache_key: str) -> pd.DataFrame:
        df = ak.stock_zh_a_spot_em()
        df = df.rename(columns=FIELD_MAPPING["stock_zh_a_spot_em"])
        return df

    @staticmethod
    def _format_stock_code(symbol: str) -> str:
        """
        格式化股票代码为akshare需要的格式
        上海证券交易所股票代码以6开头，需要添加sh
        深圳证券交易所股票代码以0或3开头，需要添加sz
        """
        if not symbol:
            raise ValueError("股票代码不能为空")
            
        if not symbol.isdigit():
            raise ValueError("股票代码必须是数字")
            
        if len(symbol) != 6:
            raise ValueError("股票代码必须是6位数字")
            
        if symbol.startswith('6'):
            return f"sh{symbol}"
        elif symbol.startswith(('0', '3')):
            return f"sz{symbol}"
        else:
            raise ValueError("无效的股票代码格式")

    @staticmethod
    def _format_date(date_str):
        """格式化日期字符串为YYYYMMDD格式"""
        if isinstance(date_str, date):
            return date_str.strftime('%Y%m%d')
        elif isinstance(date_str, str):
            if len(date_str) == 8 and date_str.isdigit():
                return date_str
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                return date_obj.strftime('%Y%m%d')
            except ValueError:
                raise ValueError(f"无效的日期格式: {date_str}")
        else:
            raise ValueError(f"不支持的日期类型: {type(date_str)}")

    @staticmethod
    async def get_stock_history(
            symbol: str = None,
            start_date: str = None,
            end_date: str = None,
            adjust: str = None,
    ):
        if adjust == 'none':
            adjust = ''
            
        try:
            # 格式化股票代码和日期
            formatted_symbol = StockHistService._format_stock_code(symbol)
            formatted_start_date = StockHistService._format_date(start_date)
            formatted_end_date = StockHistService._format_date(end_date)
            
            print(f"原始股票代码: {symbol}, 格式化后: {formatted_symbol}")
            print(f"原始日期范围: {start_date} 至 {end_date}")
            print(f"格式化后日期范围: {formatted_start_date} 至 {formatted_end_date}")
            
            # 尝试使用不同的方式获取数据
            df = None
            try:
                print(f"尝试使用akshare获取数据: {symbol}, {formatted_start_date}, {formatted_end_date}, {adjust}")
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period='daily',
                    start_date=formatted_start_date,
                    end_date=formatted_end_date,
                    adjust=adjust
                )
            except Exception as e1:
                print(f"第一次尝试失败: {str(e1)}")
                df = None

            # 若抓取失败或返回空
            if df is None or df.empty:
                raise ValueError(f"未找到股票 {symbol} 在指定日期范围内的数据")
                
            # 统一列名
            if '日期' in df.columns:
                df = df.rename(columns=FIELD_MAPPING["stock_zh_a_hist"])
            elif 'date' not in df.columns:
                # 如果列名不匹配，尝试手动映射
                column_mapping = {
                    'date': 'date',
                    'open': 'open',
                    'close': 'close',
                    'high': 'high',
                    'low': 'low',
                    'volume': 'volume'
                }
                df = df.rename(columns=column_mapping)
            
            # 确保必要的列存在
            required_columns = ['date', 'close', 'open', 'high', 'low', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"数据缺少必要的列: {', '.join(missing_columns)}")
                
            # 确保数据类型正确
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            df['open'] = pd.to_numeric(df['open'], errors='coerce')
            df['high'] = pd.to_numeric(df['high'], errors='coerce')
            df['low'] = pd.to_numeric(df['low'], errors='coerce')
            df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
            
            # 删除无效数据
            df = df.dropna(subset=['close', 'open', 'high', 'low', 'volume'])
            
            if df.empty:
                raise ValueError("处理后的数据为空")
                
            return df
            
        except Exception as e:
            print(f"获取股票数据失败: {str(e)}")
            raise ValueError(f"获取股票数据失败: {str(e)}")

    @staticmethod
    def _handle_nan_values(data):
        """
        将数据中的 nan 值转换为 None
        """
        if isinstance(data, dict):
            return {k: StockHistService._handle_nan_values(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [StockHistService._handle_nan_values(item) for item in data]
        elif isinstance(data, float) and np.isnan(data):
            return None
        return data

    @staticmethod
    async def analyze_market_predictability(symbol: str, start_date: str, end_date: str) -> Dict:
        """
        分析市场可预测性
        """
        try:
            # 获取历史数据
            df = await StockHistService.get_stock_history(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjust='qfq'
            )
            
            if len(df) < 252:  # 确保有足够的数据进行计算
                raise ValueError("数据量不足，至少需要252个交易日的数据")
            
            # 计算收益率
            df['Returns'] = df['close'].pct_change()
            returns = df['Returns'].dropna()
            
            if len(returns) < 252:
                raise ValueError("有效收益率数据不足")
            
            # 参数设置
            holding_periods = [2, 5, 10, 20, 60]  # 持有期
            window_size = 252  # 滚动窗口大小
            
            # 计算方差比率
            vr_results = {}
            pval_results = {}
            
            for q in holding_periods:
                vr_series, pval_series = StockHistService._calculate_variance_ratio(returns, q, window_size)
                vr_results[f'VR_{q}'] = vr_series
                pval_results[f'PVal_{q}'] = pval_series
                
            # 计算自相关
            acorr_results = StockHistService._calculate_autocorrelation(returns, window_size)
            
            # 计算移动平均线
            df['MA200'] = df['close'].rolling(window=200).mean()
            df['MA7'] = df['close'].rolling(window=7).mean()
            df['MA30'] = df['close'].rolling(window=30).mean()
            
            # 准备返回数据
            result = {
                'price_data': df[['date', 'close', 'MA200', 'MA7', 'MA30']].to_dict('records'),
                'variance_ratio': {k: v.to_dict() for k, v in vr_results.items()},
                'p_values': {k: v.to_dict() for k, v in pval_results.items()},
                'autocorrelation': acorr_results,
                'market_state': StockHistService._analyze_market_state(vr_results, pval_results, acorr_results)
            }
            
            # 处理 nan 值
            result = StockHistService._handle_nan_values(result)
            
            return result
            
        except Exception as e:
            print(f"分析市场可预测性失败: {str(e)}")
            raise ValueError(f"分析市场可预测性失败: {str(e)}")
    
    @staticmethod
    def _calculate_variance_ratio(returns: pd.Series, q: int, window: int) -> Tuple[pd.Series, pd.Series]:
        """
        计算滚动方差比率
        基于 Lo & MacKinlay (1988) 的方法
        """
        vr_series = pd.Series(index=returns.index, dtype=float)
        pval_series = pd.Series(index=returns.index, dtype=float)
        
        for i in range(window + q, len(returns)):
            rolling_ret = returns.iloc[i - window - q:i - q]
            var_1 = rolling_ret.var()
            
            if var_1 == 0:
                continue
                
            # 汇总q期收益率
            ret_q = rolling_ret.rolling(window=q).sum().dropna()
            var_q = ret_q.var()
            vr = var_q / (q * var_1)
            vr_series.iloc[i] = vr
            
            # 计算Z分数和p值
            T = window
            var_vr = (2 * (2 * q - 1) * (q - 1)) / (3 * q * T)
            z_score = (vr - 1) / np.sqrt(var_vr)
            p_value = 2 * (1 - norm.cdf(abs(z_score)))
            pval_series.iloc[i] = p_value
            
        return vr_series, pval_series
    
    @staticmethod
    def _calculate_autocorrelation(returns: pd.Series, window: int) -> Dict:
        """
        计算自相关
        基于 Campbell, Lo & MacKinlay (1997) 的方法
        """
        # 计算不同时间尺度的自相关
        daily_ac = returns.rolling(window).apply(lambda x: pd.Series(x).autocorr(lag=1))
        weekly_ac = returns.rolling(window*5).apply(lambda x: pd.Series(x).autocorr(lag=5))
        monthly_ac = returns.rolling(window*20).apply(lambda x: pd.Series(x).autocorr(lag=20))
        
        # 计算平均自相关（1-3阶）
        def avg_acorr(x):
            acorrs = [pd.Series(x).autocorr(lag=i) for i in range(1, 4)]
            return np.mean(acorrs)
            
        daily_avg_ac = returns.rolling(window).apply(avg_acorr)
        weekly_avg_ac = returns.rolling(window*5).apply(avg_acorr)
        monthly_avg_ac = returns.rolling(window*20).apply(avg_acorr)
        
        # 计算阈值
        threshold_daily = 2 / np.sqrt(window)
        threshold_weekly = 2 / np.sqrt(window*5)
        threshold_monthly = 2 / np.sqrt(window*20)
        
        return {
            'daily': daily_ac.to_dict(),
            'weekly': weekly_ac.to_dict(),
            'monthly': monthly_ac.to_dict(),
            'daily_avg': daily_avg_ac.to_dict(),
            'weekly_avg': weekly_avg_ac.to_dict(),
            'monthly_avg': monthly_avg_ac.to_dict(),
            'thresholds': {
                'daily': threshold_daily,
                'weekly': threshold_weekly,
                'monthly': threshold_monthly
            }
        }
    
    @staticmethod
    def _analyze_market_state(vr_results: Dict, pval_results: Dict, acorr_results: Dict) -> Dict:
        """
        分析市场状态
        基于方差比率和自相关的综合判断
        """
        # 获取最新的方差比率和p值
        latest_vr = {k: v.iloc[-1] for k, v in vr_results.items()}
        latest_pval = {k: v.iloc[-1] for k, v in pval_results.items()}
        
        # 获取最新的自相关值
        latest_ac = {
            'daily': acorr_results['daily'][list(acorr_results['daily'].keys())[-1]],
            'weekly': acorr_results['weekly'][list(acorr_results['weekly'].keys())[-1]],
            'monthly': acorr_results['monthly'][list(acorr_results['monthly'].keys())[-1]],
            'daily_avg': acorr_results['daily_avg'][list(acorr_results['daily_avg'].keys())[-1]],
            'weekly_avg': acorr_results['weekly_avg'][list(acorr_results['weekly_avg'].keys())[-1]],
            'monthly_avg': acorr_results['monthly_avg'][list(acorr_results['monthly_avg'].keys())[-1]]
        }
        
        # 分析市场状态
        momentum_signals = 0
        reversion_signals = 0
        random_signals = 0
        total_signals = 0
        
        # 分析方差比率
        for period, vr in latest_vr.items():
            pval = latest_pval[f'PVal_{period.split("_")[1]}']
            if pval < 0.05:  # 显著性检验
                total_signals += 1
                if vr > 1.05:  # 动量特征
                    momentum_signals += 1
                elif vr < 0.95:  # 均值回归特征
                    reversion_signals += 1
                else:
                    random_signals += 1
        
        # 分析自相关
        for timeframe in ['daily', 'weekly', 'monthly']:
            threshold = acorr_results['thresholds'][timeframe]
            ac = latest_ac[timeframe]
            avg_ac = latest_ac[f'{timeframe}_avg']
            
            if abs(ac) > threshold or abs(avg_ac) > threshold:
                total_signals += 1
                if ac > 0 or avg_ac > 0:
                    momentum_signals += 1
                else:
                    reversion_signals += 1
            else:
                total_signals += 1
                random_signals += 1
        
        # 确保至少有一个信号
        if total_signals == 0:
            total_signals = 1
            random_signals = 1
        
        # 计算比率
        momentum_ratio = momentum_signals / total_signals
        reversion_ratio = reversion_signals / total_signals
        random_ratio = random_signals / total_signals
        
        # 确定主导市场状态
        dominant_state = 'momentum' if momentum_ratio > 0.4 else 'reversion' if reversion_ratio > 0.4 else 'random'
        
        # 返回分析结果
        return {
            'momentum_ratio': momentum_ratio,
            'reversion_ratio': reversion_ratio,
            'random_ratio': random_ratio,
            'dominant_state': dominant_state,
            'latest_metrics': {
                'variance_ratio': latest_vr,
                'p_values': latest_pval,
                'autocorrelation': latest_ac
            }
        }