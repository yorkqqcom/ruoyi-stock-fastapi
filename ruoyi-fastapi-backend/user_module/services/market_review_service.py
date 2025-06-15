import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import redis
import json
import hashlib

# Redis配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None

# 缓存过期时间（秒）
CACHE_EXPIRE = {
    'index_data': 300,  # 5分钟
    'market_sentiment': 300,  # 5分钟
    'market_fund_flow': 300,  # 5分钟
    'north_money_flow': 300,  # 5分钟
    'daily_review': 300,  # 5分钟
    'index_min_data': 60,  # 1分钟
    'concept_board_data': 300,  # 5分钟
    'sector_fund_flow': 300,  # 5分钟
    'limit_up_down_stocks': 300,  # 5分钟
    'lhb_data': 300,  # 5分钟
    'market_analysis': 300,  # 5分钟
}

# 初始化Redis连接
try:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )
except Exception as e:
    print(f"Redis连接失败: {str(e)}")
    redis_client = None

class MarketReviewService:
    @staticmethod
    def _get_cache_key(method_name: str, *args, **kwargs) -> str:
        """
        生成缓存键
        """
        # 将参数转换为字符串
        args_str = str(args) + str(sorted(kwargs.items()))
        # 使用MD5生成唯一的缓存键
        return f"market_review:{method_name}:{hashlib.md5(args_str.encode()).hexdigest()}"

    @staticmethod
    def _get_cache(method_name: str, *args, **kwargs) -> Dict:
        """
        从缓存获取数据
        """
        if redis_client is None:
            return None
            
        cache_key = MarketReviewService._get_cache_key(method_name, *args, **kwargs)
        cached_data = redis_client.get(cache_key)
        
        if cached_data:
            try:
                return json.loads(cached_data)
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _set_cache(method_name: str, data: Dict, *args, **kwargs) -> None:
        """
        设置缓存数据
        """
        if redis_client is None:
            return
            
        cache_key = MarketReviewService._get_cache_key(method_name, *args, **kwargs)
        expire_time = CACHE_EXPIRE.get(method_name, 300)  # 默认5分钟
        
        try:
            redis_client.setex(
                cache_key,
                expire_time,
                json.dumps(data)
            )
        except Exception as e:
            print(f"设置缓存失败: {str(e)}")

    @staticmethod
    def _handle_nan(value):
        """
        处理NaN值，将其转换为None
        """
        if pd.isna(value) or np.isnan(value):
            return None
        return value

    @staticmethod
    def _process_dict(data: Dict) -> Dict:
        """
        递归处理字典中的所有NaN值
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = MarketReviewService._process_dict(value)
            elif isinstance(value, (int, float)):
                result[key] = MarketReviewService._handle_nan(value)
            elif isinstance(value, list):
                result[key] = [
                    MarketReviewService._process_dict(item) if isinstance(item, dict)
                    else MarketReviewService._handle_nan(item) if isinstance(item, (int, float))
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    @staticmethod
    async def get_index_data(symbols: List[str] = None) -> Dict:
        """
        获取大盘指数数据
        """
        # 尝试从缓存获取数据
        cached_data = MarketReviewService._get_cache('index_data', symbols)
        if cached_data is not None:
            return cached_data

        if symbols is None:
            symbols = ["sh000001", "sz399001", "sz399006"]  # 上证指数、深证成指、创业板指
            
        result = []
        try:
            # 获取上证指数数据
            df_sh = ak.stock_zh_index_daily_em(symbol="sh000001")
            if not df_sh.empty:
                # 计算技术指标
                df_sh['MA5'] = df_sh['close'].rolling(window=5).mean()
                df_sh['MA10'] = df_sh['close'].rolling(window=10).mean()
                df_sh['MA20'] = df_sh['close'].rolling(window=20).mean()
                
                # 获取最新数据
                latest_sh = df_sh.iloc[-1]
                result.append({
                    'name': '上证指数',
                    'date': latest_sh['date'],
                    'value': float(latest_sh['close']),
                    'change': float((latest_sh['close'] - df_sh.iloc[-2]['close']) / df_sh.iloc[-2]['close'] * 100),
                    'volume': int(latest_sh['volume']),
                    'amount': float(latest_sh['amount']),
                    'ma5': float(latest_sh['MA5']),
                    'ma10': float(latest_sh['MA10']),
                    'ma20': float(latest_sh['MA20'])
                })

            # 获取深证成指数据
            df_sz = ak.stock_zh_index_daily_em(symbol="sz399001")
            if not df_sz.empty:
                # 计算技术指标
                df_sz['MA5'] = df_sz['close'].rolling(window=5).mean()
                df_sz['MA10'] = df_sz['close'].rolling(window=10).mean()
                df_sz['MA20'] = df_sz['close'].rolling(window=20).mean()
                
                # 获取最新数据
                latest_sz = df_sz.iloc[-1]
                result.append({
                    'name': '深证成指',
                    'date': latest_sz['date'],
                    'value': float(latest_sz['close']),
                    'change': float((latest_sz['close'] - df_sz.iloc[-2]['close']) / df_sz.iloc[-2]['close'] * 100),
                    'volume': int(latest_sz['volume']),
                    'amount': float(latest_sz['amount']),
                    'ma5': float(latest_sz['MA5']),
                    'ma10': float(latest_sz['MA10']),
                    'ma20': float(latest_sz['MA20'])
                })

            # 获取创业板指数据
            df_cyb = ak.stock_zh_index_daily_em(symbol="sz399006")
            if not df_cyb.empty:
                # 计算技术指标
                df_cyb['MA5'] = df_cyb['close'].rolling(window=5).mean()
                df_cyb['MA10'] = df_cyb['close'].rolling(window=10).mean()
                df_cyb['MA20'] = df_cyb['close'].rolling(window=20).mean()
                
                # 获取最新数据
                latest_cyb = df_cyb.iloc[-1]
                result.append({
                    'name': '创业板指',
                    'date': latest_cyb['date'],
                    'value': float(latest_cyb['close']),
                    'change': float((latest_cyb['close'] - df_cyb.iloc[-2]['close']) / df_cyb.iloc[-2]['close'] * 100),
                    'volume': int(latest_cyb['volume']),
                    'amount': float(latest_cyb['amount']),
                    'ma5': float(latest_cyb['MA5']),
                    'ma10': float(latest_cyb['MA10']),
                    'ma20': float(latest_cyb['MA20'])
                })

            # 准备图表数据
            chart_data = {
                'dates': df_sh['date'].tolist()[-750:],  # 最近3年交易日（约750个交易日）
                'shValue': df_sh['close'].tolist()[-750:],
                'szValue': df_sz['close'].tolist()[-750:],
                'cybValue': df_cyb['close'].tolist()[-750:]
            }

            response_data = {
                'cards': result,
                'chart': chart_data
            }
            
            # 设置缓存
            MarketReviewService._set_cache('index_data', response_data, symbols)
            
            return response_data
                
        except Exception as e:
            print(f"获取指数数据失败: {str(e)}")
            return {'cards': [], 'chart': {'dates': [], 'shValue': [], 'szValue': [], 'cybValue': []}}

    @staticmethod
    async def get_market_sentiment() -> Dict:
        """
        获取市场情绪数据
        """
        # 尝试从缓存获取数据
        cached_data = MarketReviewService._get_cache('market_sentiment')
        if cached_data is not None:
            return cached_data

        try:
            df = ak.stock_market_activity_legu()
            
            if df.empty:
                return {
                    'upLimit': 0,
                    'downLimit': 0,
                    'upCount': 0,
                    'downCount': 0
                }
                
            # 转换为字典格式
            result = {
                'upLimit': 0,
                'downLimit': 0,
                'upCount': 0,
                'downCount': 0
            }
            
            for _, row in df.iterrows():
                if row['item'] == '涨停':
                    result['upLimit'] = int(float(row['value']))
                elif row['item'] == '跌停':
                    result['downLimit'] = int(float(row['value']))
                elif row['item'] == '上涨':
                    result['upCount'] = int(float(row['value']))
                elif row['item'] == '下跌':
                    result['downCount'] = int(float(row['value']))
            
            processed_result = MarketReviewService._process_dict(result)
            
            # 设置缓存
            MarketReviewService._set_cache('market_sentiment', processed_result)
            
            return processed_result
        except Exception as e:
            print(f"获取市场情绪数据失败: {str(e)}")
            return {
                'upLimit': 0,
                'downLimit': 0,
                'upCount': 0,
                'downCount': 0
            }

    @staticmethod
    async def get_market_fund_flow() -> Dict:
        """
        获取大盘资金流向数据
        """
        # 尝试从缓存获取数据
        cached_data = MarketReviewService._get_cache('market_fund_flow')
        if cached_data is not None:
            return cached_data

        try:
            # 获取资金流向数据
            fund_flow_df = ak.stock_individual_fund_flow_rank(indicator="今日")
            
            # 获取融资融券账户信息
            margin_account_df = ak.stock_margin_account_info()
            
            # 获取最新的融资融券数据
            if not margin_account_df.empty:
                # 按日期降序排序
                margin_account_df = margin_account_df.sort_values('日期', ascending=False)
                latest_margin = margin_account_df.iloc[0]
                
                # 计算30日平均值
                last_30_days = margin_account_df.head(30)
                
                # 计算各项指标的30日平均值
                trading_investor_count_avg = round(last_30_days['参与交易的投资者数量'].mean()) if not last_30_days.empty else 0
                debt_investor_count_avg = round(last_30_days['有融资融券负债的投资者数量'].mean()) if not last_30_days.empty else 0
                collateral_value_avg = round(last_30_days['担保物总价值'].mean(), 2) if not last_30_days.empty else 0
                maintenance_ratio_avg = round(last_30_days['平均维持担保比例'].mean(), 2) if not last_30_days.empty else 0
                
                # 计算融资融券相关指标的30日平均值
                financing_balance_avg = round(last_30_days['融资余额'].mean(), 2) if not last_30_days.empty else 0
                securities_balance_avg = round(last_30_days['融券余额'].mean(), 2) if not last_30_days.empty else 0
                
                margin_account = {
                    'date': latest_margin['日期'],
                    'financing_balance': float(latest_margin['融资余额']),
                    'securities_balance': float(latest_margin['融券余额']),
                    'financing_buy': float(latest_margin['融资买入额']),
                    'securities_sell': float(latest_margin['融券卖出额']),
                    'broker_count': int(latest_margin['证券公司数量']),
                    'branch_count': int(latest_margin['营业部数量']),
                    'individual_investor_count': int(latest_margin['个人投资者数量']),
                    'institution_investor_count': int(latest_margin['机构投资者数量']),
                    'trading_investor_count': int(latest_margin['参与交易的投资者数量']),
                    'debt_investor_count': int(latest_margin['有融资融券负债的投资者数量']),
                    'collateral_value': float(latest_margin['担保物总价值']),
                    'maintenance_ratio': float(latest_margin['平均维持担保比例']),
                    'trading_investor_count_avg': trading_investor_count_avg,
                    'debt_investor_count_avg': debt_investor_count_avg,
                    'collateral_value_avg': collateral_value_avg,
                    'maintenance_ratio_avg': maintenance_ratio_avg,
                    'financing_balance_avg': financing_balance_avg,
                    'securities_balance_avg': securities_balance_avg
                }
            else:
                margin_account = {
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'financing_balance': 0,
                    'securities_balance': 0,
                    'financing_buy': 0,
                    'securities_sell': 0,
                    'broker_count': 0,
                    'branch_count': 0,
                    'individual_investor_count': 0,
                    'institution_investor_count': 0,
                    'trading_investor_count': 0,
                    'debt_investor_count': 0,
                    'collateral_value': 0,
                    'maintenance_ratio': 0,
                    'trading_investor_count_avg': 0,
                    'debt_investor_count_avg': 0,
                    'collateral_value_avg': 0,
                    'maintenance_ratio_avg': 0,
                    'financing_balance_avg': 0,
                    'securities_balance_avg': 0
                }
            
            # 处理资金流向数据
            if not fund_flow_df.empty:
                # 检查并重命名列名
                column_mapping = {
                    '主力净流入-净额': 'net_amount',
                    '主力净流入-净占比': 'net_ratio',
                    '涨跌幅': 'change_percent'
                }
                
                # 重命名列
                for old_col, new_col in column_mapping.items():
                    if old_col in fund_flow_df.columns:
                        fund_flow_df[new_col] = fund_flow_df[old_col]
                
                # 转换数据类型
                fund_flow_df['net_amount'] = pd.to_numeric(fund_flow_df['net_amount'], errors='coerce')
                fund_flow_df['net_ratio'] = pd.to_numeric(fund_flow_df['net_ratio'], errors='coerce')
                fund_flow_df['change_percent'] = pd.to_numeric(fund_flow_df['change_percent'], errors='coerce')
                
                # 处理异常值
                fund_flow_df = fund_flow_df.replace([np.inf, -np.inf], np.nan)
                fund_flow_df = fund_flow_df.fillna(0)
                
                # 计算总的主力资金净流入
                total_main_net_inflow = fund_flow_df['net_amount'].sum()
                
                # 获取行业和概念资金流向
                industry_flow = fund_flow_df[fund_flow_df['类型'] == '行业'].to_dict('records')
                concept_flow = fund_flow_df[fund_flow_df['类型'] == '概念'].to_dict('records')
                
                # 获取资金流入前10的板块
                top_inflow = fund_flow_df.nlargest(10, 'net_amount').to_dict('records')
                
                # 计算净流入和净流出
                net_inflow = fund_flow_df[fund_flow_df['net_amount'] > 0]['net_amount'].sum()
                net_outflow = fund_flow_df[fund_flow_df['net_amount'] < 0]['net_amount'].sum()
                
                # 计算净流入和净流出的30日平均值
                if not fund_flow_df.empty:
                    # 获取最近30个交易日的数据
                    last_30_days_flow = fund_flow_df.head(30)
                    
                    # 计算30日平均净流入和净流出
                    net_inflow_avg = round(last_30_days_flow[last_30_days_flow['net_amount'] > 0]['net_amount'].mean() / 100000000, 2) if not last_30_days_flow.empty else 0
                    net_outflow_avg = round(last_30_days_flow[last_30_days_flow['net_amount'] < 0]['net_amount'].mean() / 100000000, 2) if not last_30_days_flow.empty else 0
                    
                    response_data = {
                        'top_inflow': top_inflow,
                        'industry_flow': industry_flow,
                        'concept_flow': concept_flow,
                        'margin_account': margin_account,
                        'amount': round(total_main_net_inflow / 100000000, 2),  # 转换为亿元
                        'netInflow': round(net_inflow / 100000000, 2),  # 转换为亿元
                        'netOutflow': round(net_outflow / 100000000, 2),  # 转换为亿元
                        'netInflow_avg': net_inflow_avg,
                        'netOutflow_avg': net_outflow_avg,
                        'latestDate': datetime.now().strftime('%Y-%m-%d')
                    }
                    
                    # 设置缓存
                    MarketReviewService._set_cache('market_fund_flow', response_data)
                    
                    return response_data
            return {
                'top_inflow': [],
                'industry_flow': [],
                'concept_flow': [],
                'margin_account': margin_account,
                'amount': 0,
                'netInflow': 0,
                'netOutflow': 0,
                'latestDate': datetime.now().strftime('%Y-%m-%d')
            }
        except Exception as e:
            print(f"获取资金流向数据失败: {str(e)}")
            # 创建一个默认的 margin_account 字典
            default_margin_account = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'financing_balance': 0,
                'securities_balance': 0,
                'financing_buy': 0,
                'securities_sell': 0,
                'broker_count': 0,
                'branch_count': 0,
                'individual_investor_count': 0,
                'institution_investor_count': 0,
                'trading_investor_count': 0,
                'debt_investor_count': 0,
                'collateral_value': 0,
                'maintenance_ratio': 0,
                'trading_investor_count_avg': 0,
                'debt_investor_count_avg': 0,
                'collateral_value_avg': 0,
                'maintenance_ratio_avg': 0,
                'financing_balance_avg': 0,
                'securities_balance_avg': 0,
                'financing_buy_avg': 0,
                'securities_sell_avg': 0,
                'broker_count_avg': 0,
                'branch_count_avg': 0,
                'individual_investor_count_avg': 0,
                'institution_investor_count_avg': 0
            }
            return {
                'top_inflow': [],
                'industry_flow': [],
                'concept_flow': [],
                'margin_account': default_margin_account,
                'amount': 0,
                'netInflow': 0,
                'netOutflow': 0,
                'latestDate': datetime.now().strftime('%Y-%m-%d')
            }

    @staticmethod
    async def get_north_money_flow() -> Dict:
        """
        获取北向资金流向数据
        """
        try:
            # 获取北向资金数据
            df = ak.stock_hsgt_fund_flow_summary_em()
            if df.empty:
                return {
                    'amount': 0,
                    'shAmount': 0,
                    'szAmount': 0,
                    'dates': [],
                    'northMoneyData': []
                }
            
            # 筛选北向资金数据（沪股通和深股通的北向资金）
            north_df = df[(df['资金方向'] == '北向') & (df['板块'].isin(['沪股通', '深股通']))]
            
            if north_df.empty:
                return {
                    'amount': 0,
                    'shAmount': 0,
                    'szAmount': 0,
                    'dates': [],
                    'northMoneyData': []
                }
            
            # 获取沪股通和深股通数据
            sh_df = north_df[north_df['板块'] == '沪股通']
            sz_df = north_df[north_df['板块'] == '深股通']
            
            # 获取最新数据
            sh_amount = float(sh_df.iloc[0]['成交净买额']) if not sh_df.empty else 0
            sz_amount = float(sz_df.iloc[0]['成交净买额']) if not sz_df.empty else 0
            
            # 计算总金额
            net_amount = sh_amount + sz_amount
            
            # 获取历史数据
            hist_df = ak.stock_hsgt_hist_em(symbol="北向资金")
            if not hist_df.empty:
                # 确保日期格式正确并排序
                hist_df['日期'] = pd.to_datetime(hist_df['日期']).dt.strftime('%Y-%m-%d')
                hist_df = hist_df.sort_values('日期', ascending=True)
                
                # 获取最近30个交易日数据
                latest_30 = hist_df.tail(30)
                
                # 使用当日成交净买额，单位已经是亿元
                dates = latest_30['日期'].tolist()
                north_money_data = latest_30['当日成交净买额'].fillna(0).round(2).tolist()
                
                # 获取沪股通和深股通的历史数据
                sh_hist_df = ak.stock_hsgt_hist_em(symbol="沪股通")
                sz_hist_df = ak.stock_hsgt_hist_em(symbol="深股通")
                
                if not sh_hist_df.empty and not sz_hist_df.empty:
                    # 确保日期格式正确并排序
                    sh_hist_df['日期'] = pd.to_datetime(sh_hist_df['日期']).dt.strftime('%Y-%m-%d')
                    sz_hist_df['日期'] = pd.to_datetime(sz_hist_df['日期']).dt.strftime('%Y-%m-%d')
                    
                    # 获取最近30个交易日数据
                    sh_latest_30 = sh_hist_df.tail(30)
                    sz_latest_30 = sz_hist_df.tail(30)
                    
                    # 使用当日成交净买额，单位已经是亿元
                    sh_amount = float(sh_latest_30.iloc[-1]['当日成交净买额']) if not sh_latest_30.empty else 0
                    sz_amount = float(sz_latest_30.iloc[-1]['当日成交净买额']) if not sz_latest_30.empty else 0
                    
                    # 更新总金额
                    net_amount = sh_amount + sz_amount
            else:
                dates = [north_df.iloc[0]['交易日']]
                north_money_data = [net_amount]
            
            result = {
                'amount': round(net_amount, 2),
                'shAmount': round(sh_amount, 2),
                'szAmount': round(sz_amount, 2),
                'dates': dates,
                'northMoneyData': north_money_data
            }
            
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取北向资金数据失败: {str(e)}")
            return {
                'amount': 0,
                'shAmount': 0,
                'szAmount': 0,
                'dates': [],
                'northMoneyData': []
            }

    @staticmethod
    async def get_daily_review() -> Dict:
        """
        获取每日复盘数据
        """
        try:
            # 并行获取各类数据
            index_data = await MarketReviewService.get_index_data()
            sentiment_data = await MarketReviewService.get_market_sentiment()
            north_money = await MarketReviewService.get_north_money_flow()
            fund_flow = await MarketReviewService.get_market_fund_flow()
            
            result = {
                'index_data': index_data,
                'sentiment_data': sentiment_data,
                'north_money': north_money,
                'fund_flow': fund_flow,
                'review_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取每日复盘数据失败: {str(e)}")
            return {}

    @staticmethod
    async def get_index_min_data(symbol: str = "000001", period: str = "1") -> Dict:
        """
        获取指数分时行情数据
        :param symbol: 指数代码，如"000001"表示上证指数
        :param period: 周期，可选值：'1', '5', '15', '30', '60'
        :return: 分时行情数据
        """
        try:
            # 获取当前日期
            today = datetime.now()
            
            # 检查是否为交易日
            if today.weekday() >= 5:  # 周六日
                # 获取最近一个交易日的数据
                start_date = f"{today.strftime('%Y-%m-%d')} 09:30:00"
                end_date = f"{today.strftime('%Y-%m-%d')} 15:00:00"
            else:
                # 检查是否在交易时间内
                current_time = today.strftime('%H:%M:%S')
                if current_time < '09:30:00' or current_time > '15:00:00':
                    # 获取最近一个交易日的数据
                    start_date = f"{today.strftime('%Y-%m-%d')} 09:30:00"
                    end_date = f"{today.strftime('%Y-%m-%d')} 15:00:00"
                else:
                    # 交易时间内，获取当日数据
                    start_date = f"{today.strftime('%Y-%m-%d')} 09:30:00"
                    end_date = f"{today.strftime('%Y-%m-%d')} 15:00:00"
            
            # 获取分时数据
            df = ak.index_zh_a_hist_min_em(
                symbol=symbol,
                period=period,
                start_date=start_date,
                end_date=end_date
            )
            
            if df.empty:
                # 尝试获取最近一个交易日的数据
                yesterday = today - timedelta(days=1)
                start_date = f"{yesterday.strftime('%Y-%m-%d')} 09:30:00"
                end_date = f"{yesterday.strftime('%Y-%m-%d')} 15:00:00"
                
                df = ak.index_zh_a_hist_min_em(
                    symbol=symbol,
                    period=period,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if df.empty:
                    return {
                        'times': [],
                        'prices': [],
                        'volumes': [],
                        'amounts': [],
                        'high': 0,
                        'low': 0,
                        'open': 0,
                        'close': 0
                    }
            
            # 数据清洗和验证
            df = df.fillna(method='ffill')  # 使用前值填充缺失值
            df = df.fillna(method='bfill')  # 使用后值填充剩余的缺失值
            
            # 确保数值类型正确
            df['收盘'] = pd.to_numeric(df['收盘'], errors='coerce')
            df['成交量'] = pd.to_numeric(df['成交量'], errors='coerce')
            df['成交额'] = pd.to_numeric(df['成交额'], errors='coerce')
            df['最高'] = pd.to_numeric(df['最高'], errors='coerce')
            df['最低'] = pd.to_numeric(df['最低'], errors='coerce')
            df['开盘'] = pd.to_numeric(df['开盘'], errors='coerce')
            
            # 处理异常值
            df = df.replace([np.inf, -np.inf], np.nan)
            df = df.fillna(0)
            
            # 处理数据
            result = {
                'times': df['时间'].tolist(),
                'prices': df['收盘'].round(2).tolist(),
                'volumes': df['成交量'].astype(int).tolist(),
                'amounts': df['成交额'].round(2).tolist(),
                'high': float(df['最高'].max()),
                'low': float(df['最低'].min()),
                'open': float(df['开盘'].iloc[0]),
                'close': float(df['收盘'].iloc[-1])
            }
            
            # 验证数据完整性
            if not all(len(v) == len(result['times']) for v in [result['prices'], result['volumes'], result['amounts']]):
                return {
                    'times': [],
                    'prices': [],
                    'volumes': [],
                    'amounts': [],
                    'high': 0,
                    'low': 0,
                    'open': 0,
                    'close': 0
                }
            
            return MarketReviewService._process_dict(result)
            
        except Exception as e:
            print(f"获取分时行情数据失败: {str(e)}")
            return {
                'times': [],
                'prices': [],
                'volumes': [],
                'amounts': [],
                'high': 0,
                'low': 0,
                'open': 0,
                'close': 0
            }

    @staticmethod
    async def get_concept_board_data() -> Dict:
        """
        获取概念板块数据
        """
        try:
            df = ak.stock_board_concept_name_em()
            if df.empty:
                return {
                    'concept_boards': [],
                    'top_gainers': [],
                    'top_losers': []
                }
            
            # 处理数据
            df['涨跌幅'] = df['涨跌幅'].astype(float)
            df['总市值'] = df['总市值'].astype(float)
            df['换手率'] = df['换手率'].astype(float)
            
            # 获取涨跌幅前10和后10的板块
            top_gainers = df.nlargest(10, '涨跌幅')
            top_losers = df.nsmallest(10, '涨跌幅')
            
            # 转换为字典格式
            result = {
                'concept_boards': df.to_dict('records'),
                'top_gainers': top_gainers.to_dict('records'),
                'top_losers': top_losers.to_dict('records')
            }
            
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取概念板块数据失败: {str(e)}")
            return {
                'concept_boards': [],
                'top_gainers': [],
                'top_losers': []
            }

    @staticmethod
    async def get_sector_fund_flow() -> Dict:
        """
        获取板块资金流向数据
        """
        try:
            # 获取行业资金流数据
            industry_df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流")
            # 获取概念资金流数据
            concept_df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
            
            if industry_df.empty or concept_df.empty:
                return {
                    'industry_flow': [],
                    'concept_flow': [],
                    'top_inflow': []
                }
            
            # 检查必要字段是否存在
            required_columns = ['名称', '今日涨跌幅', '今日主力净流入-净额', '今日主力净流入-净占比']
            for df in [industry_df, concept_df]:
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return {
                        'industry_flow': [],
                        'concept_flow': [],
                        'top_inflow': []
                    }
            
            # 处理数据
            try:
                # 重命名列以匹配前端期望的格式
                column_mapping = {
                    '今日涨跌幅': '涨跌幅',
                    '今日主力净流入-净额': '主力净流入-净额',
                    '今日主力净流入-净占比': '主力净流入-净占比',
                    '今日主力净流入最大股': '主力净流入最大股'
                }
                
                industry_df = industry_df.rename(columns=column_mapping)
                concept_df = concept_df.rename(columns=column_mapping)
                
                # 转换数据类型
                industry_df['主力净流入-净额'] = pd.to_numeric(industry_df['主力净流入-净额'], errors='coerce')
                concept_df['主力净流入-净额'] = pd.to_numeric(concept_df['主力净流入-净额'], errors='coerce')
                
                # 处理异常值
                industry_df = industry_df.replace([np.inf, -np.inf], np.nan)
                concept_df = concept_df.replace([np.inf, -np.inf], np.nan)
                
                # 填充缺失值
                industry_df = industry_df.fillna(0)
                concept_df = concept_df.fillna(0)
                
                # 合并数据并获取资金流入前10的板块
                combined_df = pd.concat([industry_df, concept_df])
                top_inflow = combined_df.nlargest(10, '主力净流入-净额')
                
                # 转换数据为字典格式
                result = {
                    'industry_flow': industry_df.to_dict('records'),
                    'concept_flow': concept_df.to_dict('records'),
                    'top_inflow': top_inflow.to_dict('records')
                }
                
                return MarketReviewService._process_dict(result)
            except (ValueError, TypeError) as e:
                print(f"数据处理失败: {str(e)}")
                return {
                    'industry_flow': [],
                    'concept_flow': [],
                    'top_inflow': []
                }
        except Exception as e:
            print(f"获取板块资金流向数据失败: {str(e)}")
            return {
                'industry_flow': [],
                'concept_flow': [],
                'top_inflow': []
            }

    @staticmethod
    async def get_limit_up_down_stocks() -> Dict:
        """
        获取涨停跌停股票数据
        """
        try:
            today = datetime.now().strftime('%Y%m%d')
            
            # 获取涨停股票数据
            limit_up_df = ak.stock_zt_pool_em(date=today)
            # 获取跌停股票数据
            limit_down_df = ak.stock_zt_pool_dtgc_em(date=today)
            
            if limit_up_df.empty and limit_down_df.empty:
                return {
                    'limit_up_stocks': [],
                    'limit_down_stocks': [],
                    'continuous_limit_up': []
                }
            
            # 处理涨停股票数据
            if not limit_up_df.empty:
                limit_up_df['连板数'] = limit_up_df['连板数'].astype(int)
                continuous_limit_up = limit_up_df[limit_up_df['连板数'] > 1]
            else:
                continuous_limit_up = pd.DataFrame()
            
            result = {
                'limit_up_stocks': limit_up_df.to_dict('records') if not limit_up_df.empty else [],
                'limit_down_stocks': limit_down_df.to_dict('records') if not limit_down_df.empty else [],
                'continuous_limit_up': continuous_limit_up.to_dict('records') if not continuous_limit_up.empty else []
            }
            
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取涨停跌停股票数据失败: {str(e)}")
            return {
                'limit_up_stocks': [],
                'limit_down_stocks': [],
                'continuous_limit_up': []
            }

    @staticmethod
    async def get_lhb_data() -> Dict:
        """
        获取龙虎榜数据
        """
        try:
            today = datetime.now().strftime('%Y%m%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
            
            # 获取龙虎榜详情
            lhb_df = ak.stock_lhb_detail_em(start_date=yesterday, end_date=today)
            
            # 获取机构买卖统计
            try:
                jg_df = ak.stock_lhb_jgmmtj_em(start_date=yesterday, end_date=today)
                
                if not jg_df.empty:
                    # 检查必要列是否存在
                    required_columns = ['代码', '名称', '收盘价', '涨跌幅', '机构买入总额', '机构卖出总额', '机构买入净额']
                    missing_columns = [col for col in required_columns if col not in jg_df.columns]
                    if missing_columns:
                        jg_df = pd.DataFrame()
                    else:
                        # 转换数据类型
                        jg_df['收盘价'] = pd.to_numeric(jg_df['收盘价'], errors='coerce')
                        jg_df['涨跌幅'] = pd.to_numeric(jg_df['涨跌幅'], errors='coerce')
                        jg_df['机构买入总额'] = pd.to_numeric(jg_df['机构买入总额'], errors='coerce')
                        jg_df['机构卖出总额'] = pd.to_numeric(jg_df['机构卖出总额'], errors='coerce')
                        jg_df['机构买入净额'] = pd.to_numeric(jg_df['机构买入净额'], errors='coerce')
                        
                        # 重命名列以匹配前端期望的格式
                        jg_df = jg_df.rename(columns={
                            '机构买入总额': '买入额',
                            '机构卖出总额': '卖出额',
                            '机构买入净额': '净买入额'
                        })
                        
                        # 添加机构名称列
                        jg_df['机构名称'] = '机构' + jg_df['代码'].astype(str)
            except Exception as e:
                print(f"获取机构买卖统计数据失败: {str(e)}")
                jg_df = pd.DataFrame()
            
            # 获取营业部排行
            yyb_df = ak.stock_lh_yyb_most()
            
            # 数据验证
            if lhb_df.empty and jg_df.empty and yyb_df.empty:
                return {
                    'lhb_details': [],
                    'institution_trading': [],
                    'broker_ranking': []
                }
            
            # 处理龙虎榜详情数据
            if not lhb_df.empty:
                # 检查必要列是否存在
                required_columns = ['代码', '名称', '收盘价', '涨跌幅', '龙虎榜净买额']
                missing_columns = [col for col in required_columns if col not in lhb_df.columns]
                if missing_columns:
                    lhb_df = pd.DataFrame()
                else:
                    # 转换数据类型
                    lhb_df['收盘价'] = pd.to_numeric(lhb_df['收盘价'], errors='coerce')
                    lhb_df['涨跌幅'] = pd.to_numeric(lhb_df['涨跌幅'], errors='coerce')
                    lhb_df['龙虎榜净买额'] = pd.to_numeric(lhb_df['龙虎榜净买额'], errors='coerce')
            
            # 处理营业部排行数据
            yyb_df = pd.DataFrame(yyb_df)
            if not yyb_df.empty:
                # 将合计动用资金转换为数值类型
                def convert_amount(amount_str):
                    if pd.isna(amount_str):
                        return 0
                    if isinstance(amount_str, (int, float)):
                        return amount_str
                    if '亿' in amount_str:
                        return float(amount_str.replace('亿', '')) * 100000000
                    elif '万' in amount_str:
                        return float(amount_str.replace('万', '')) * 10000
                    return float(amount_str)

                yyb_df['合计动用资金'] = yyb_df['合计动用资金'].apply(convert_amount)
                
                # 将年内3日跟买成功率转换为数值类型
                def convert_success_rate(rate_str):
                    if pd.isna(rate_str) or rate_str == '无符合数据':
                        return 0
                    try:
                        return float(rate_str.rstrip('%')) / 100
                    except (ValueError, TypeError):
                        return 0
                
                yyb_df['年内3日跟买成功率'] = yyb_df['年内3日跟买成功率'].apply(convert_success_rate)
                
                # 使用正确的列名
                broker_ranking = yyb_df[['序号', '营业部名称', '上榜次数', '合计动用资金', '年内上榜次数', '年内买入股票只数', '年内3日跟买成功率']].to_dict('records')
            else:
                broker_ranking = []

            result = {
                'lhb_details': lhb_df.to_dict('records') if not lhb_df.empty else [],
                'institution_trading': jg_df.to_dict('records') if not jg_df.empty else [],
                'broker_ranking': broker_ranking
            }
            
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取龙虎榜数据失败: {str(e)}")
            return {
                'lhb_details': [],
                'institution_trading': [],
                'broker_ranking': []
            }

    @staticmethod
    async def get_market_analysis() -> Dict:
        """
        获取市场分析数据（整合所有数据）
        """
        try:
            # 并行获取各类数据
            concept_data = await MarketReviewService.get_concept_board_data()
            fund_flow_data = await MarketReviewService.get_sector_fund_flow()
            limit_stocks_data = await MarketReviewService.get_limit_up_down_stocks()
            lhb_data = await MarketReviewService.get_lhb_data()
            
            result = {
                'concept_data': concept_data,
                'fund_flow_data': fund_flow_data,
                'limit_stocks_data': limit_stocks_data,
                'lhb_data': lhb_data,
                'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return MarketReviewService._process_dict(result)
        except Exception as e:
            print(f"获取市场分析数据失败: {str(e)}")
            return {} 