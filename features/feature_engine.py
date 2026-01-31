#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特征工程引擎
基于PriceActions理论的综合特征提取和管理
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from datetime import date, datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from .price_action_features import PriceActionFeatureExtractor
from .technical_features import TechnicalFeatureExtractor
from .pattern_features import PatternFeatureExtractor
from .market_features import MarketFeatureExtractor
from .time_series_features import TimeSeriesFeatureExtractor
from .moneyflow_features import MoneyFlowFeatureExtractor
from .feature_normalizer import FeatureNormalizer
try:
    from .feature_list_loader import load_feature_list_from_file, should_include_feature, get_default_feature_list_path
except ImportError:
    # 如果相对导入失败，尝试绝对导入
    try:
        from prediction.features.feature_list_loader import load_feature_list_from_file, should_include_feature, get_default_feature_list_path
    except ImportError:
        # 如果都失败，提供替代实现
        import warnings
        warnings.warn("无法导入 feature_list_loader 模块，使用简化版本", ImportWarning)
        from pathlib import Path
        from typing import Set
        
        def load_feature_list_from_file(file_path: str) -> Set[str]:
            """简化的特征列表加载函数"""
            feature_set = set()
            if not file_path:
                return feature_set
            file_path_obj = Path(file_path)
            if not file_path_obj.is_absolute():
                # 相对路径，从项目根目录查找
                project_root = Path(__file__).parent.parent.parent
                file_path_obj = project_root / file_path
            if not file_path_obj.exists():
                warnings.warn(f"特征配置文件不存在: {file_path_obj}", UserWarning)
                return feature_set
            try:
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    for line in f:
                        raw = line.strip()
                        if raw and not raw.startswith('#'):
                            if '__' in raw or ',' in raw:
                                feature_set.add(raw)
                return feature_set
            except Exception as e:
                warnings.warn(f"加载特征列表失败: {e}", UserWarning)
                return feature_set
        
        def should_include_feature(feature_key: str, allowed_features=None) -> bool:
            """简化的特征包含判断函数"""
            if allowed_features is None:
                return True
            return feature_key in allowed_features
        
        def get_default_feature_list_path() -> str:
            """获取默认特征列表路径"""
            project_root = Path(__file__).parent.parent.parent
            return str(project_root / "config" / "train" / "featurelist_balanced_90pct_293.txt")

from dao.feature_dao import FeatureDAO
from dao.moneyflow_dao import MoneyFlowDAO
from dao.daily_quote_dao import DailyQuoteDAO
from dao.stock_basic_dao import StockBasicDAO
from utils.logger import setup_logger

logger = setup_logger()

class FeatureEngine:
    """特征工程引擎"""
    
    def __init__(self, feature_list_path: Optional[str] = None):
        """
        初始化特征工程引擎
        
        Args:
            feature_list_path: 特征列表文件路径，如果为None则使用所有特征
        """
        self.price_action_extractor = PriceActionFeatureExtractor()
        self.technical_extractor = TechnicalFeatureExtractor()
        self.pattern_extractor = PatternFeatureExtractor()
        self.market_extractor = MarketFeatureExtractor()
        self.time_series_extractor = TimeSeriesFeatureExtractor()
        self.moneyflow_extractor = MoneyFlowFeatureExtractor()
        self.feature_dao = FeatureDAO()
        self.moneyflow_dao = None  # 延迟初始化
        self.normalizer = FeatureNormalizer()
        
        # 加载允许的特征列表
        # 只有当显式传入 feature_list_path 时才加载特征列表
        # 如果 feature_list_path 为 None，则使用所有特征
        self.allowed_features: Optional[set] = None
        if feature_list_path:
            try:
                self.allowed_features = load_feature_list_from_file(feature_list_path)
                if self.allowed_features:
                    logger.info(f"已加载特征列表，共 {len(self.allowed_features)} 个允许的特征")
                else:
                    logger.warning(f"特征列表文件为空或加载失败: {feature_list_path}，将使用所有特征")
            except Exception as e:
                logger.warning(f"加载特征列表失败: {e}，将使用所有特征")
                self.allowed_features = None
        
        # 特征类别权重
        self.feature_weights = {
            'price_action': 0.18,
            'technical': 0.18,
            'pattern': 0.15,
            'market': 0.15,
            'time_series': 0.15,
            'moneyflow': 0.12,
            'volume': 0.04,
            'volatility': 0.03
        }
    
    def extract_all_features(self, df: pd.DataFrame, ts_code: str, 
                           trade_date: date, save_to_db: bool = True) -> Dict[str, Any]:
        """
        提取所有特征
        
        Args:
            df: 历史价格数据DataFrame
            ts_code: 股票代码
            trade_date: 交易日期
            save_to_db: 是否保存特征到数据库，默认为True（训练时保存，预测时设为False）
            
        Returns:
            特征字典
        """
        try:
            # 优化：统一限制历史数据范围，确保所有特征使用相同的历史窗口
            # 预测时只需要最近100天的数据（足够计算特征），训练时如果数据不足100天则使用全部
            max_history_days = 100
            if not df.empty and 'trade_date' in df.columns:
                df_dates = pd.to_datetime(df['trade_date']).dt.date
                if len(df_dates) > max_history_days:
                    # 只保留最近max_history_days天的数据
                    end_date = df_dates.max()
                    start_date = end_date - timedelta(days=max_history_days)
                    df = df[df['trade_date'] >= pd.Timestamp(start_date)].copy()
                    logger.debug(f"限制历史数据范围: 保留最近{max_history_days}天数据 ({start_date} 到 {end_date})")
            
            features = {}
            
            # 如果指定了特征列表，只计算需要的特征类别，避免不必要的计算
            # 价格行为特征
            if self._should_extract_category('price_action'):
                price_action_features = self.price_action_extractor.extract_all_features(df)
                features.update(self._add_feature_prefix(price_action_features, 'price_action'))
            
            # 技术指标特征
            if self._should_extract_category('technical'):
                technical_features = self.technical_extractor.extract_all_features(df)
                features.update(self._add_feature_prefix(technical_features, 'technical'))
            
            # 形态识别特征
            if self._should_extract_category('pattern'):
                pattern_features = self.pattern_extractor.extract_all_features(df)
                features.update(self._add_feature_prefix(pattern_features, 'pattern'))
            
            # 市场特征
            if self._should_extract_category('market'):
                market_features = self.market_extractor.extract_all_features(df)
                features.update(self._add_feature_prefix(market_features, 'market'))
                
                # 提取活跃特征（涨幅排名和涨幅阈值）
                active_features = self._extract_active_features(ts_code, trade_date)
                if active_features:
                    features.update(self._add_feature_prefix(active_features, 'market'))
            
            # 时间序列特征
            if self._should_extract_category('time_series'):
                time_series_features = self.time_series_extractor.extract_all_features(df)
                features.update(self._add_feature_prefix(time_series_features, 'time_series'))
            
            # 资金流特征（使用历史数据，与其他特征保持一致）
            if self._should_extract_category('moneyflow'):
                moneyflow_features = self._extract_moneyflow_features(df, ts_code, trade_date)
                if moneyflow_features:
                    features.update(self._add_feature_prefix(moneyflow_features, 'moneyflow'))
            
            # 特征标准化处理
            features = self.normalizer.normalize_features(features)
            
            # 特征后处理
            features = self._post_process_features(features)
            
            # 特征过滤：只保留允许的特征
            features = self._filter_features(features)
            
            # 根据参数决定是否保存特征到数据库
            if save_to_db:
                self._save_features_to_db(ts_code, trade_date, features)
                logger.info(f"提取特征成功: {ts_code} {trade_date} - {len(features)}个特征（已保存到数据库）")
            else:
                logger.info(f"提取特征成功: {ts_code} {trade_date} - {len(features)}个特征（未保存到数据库）")
            
            return features
            
        except Exception as e:
            logger.error(f"提取特征失败: {e}")
            return {}
    
    def _add_feature_prefix(self, features: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """为特征添加前缀"""
        return {f"{prefix}_{k}": v for k, v in features.items()}
    
    def _should_extract_category(self, category: str) -> bool:
        """
        判断是否需要提取某个类别的特征
        
        Args:
            category: 特征类别名称
            
        Returns:
            如果需要提取该类别，返回True；否则返回False
        """
        # 如果没有指定特征列表，提取所有类别
        if self.allowed_features is None:
            return True
        
        # 检查该类别是否有需要的特征
        # 特征键格式：category__feature_name
        for feature_key in self.allowed_features:
            if feature_key.startswith(f"{category}__"):
                return True
        
        # 该类别没有需要的特征，跳过
        return False
    
    def _filter_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        过滤特征，只保留允许的特征
        
        Args:
            features: 原始特征字典
            
        Returns:
            过滤后的特征字典
        """
        if self.allowed_features is None:
            # 如果没有限制，返回所有特征
            return features
        
        filtered_features = {}
        excluded_count = 0
        
        for feature_name, feature_value in features.items():
            # 构建特征键（格式：category__feature_name）
            category = self._get_feature_category(feature_name)
            feature_key = f"{category}__{feature_name}"
            
            # 检查是否在允许列表中
            if feature_key in self.allowed_features:
                filtered_features[feature_name] = feature_value
            else:
                excluded_count += 1
        
        if excluded_count > 0:
            logger.debug(f"过滤特征: 保留 {len(filtered_features)} 个，排除 {excluded_count} 个")
        
        return filtered_features
    
    def _post_process_features(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """特征后处理"""
        try:
            processed_features = {}
            
            for name, value in features.items():
                if isinstance(value, pd.Series):
                    # 取最后一个值
                    processed_value = value.iloc[-1] if len(value) > 0 else 0.0
                elif isinstance(value, np.ndarray):
                    # 取最后一个值
                    processed_value = value[-1] if len(value) > 0 else 0.0
                elif isinstance(value, (int, float)):
                    processed_value = float(value)
                else:
                    processed_value = 0.0
                
                # 处理异常值
                try:
                    if pd.isna(processed_value) or (isinstance(processed_value, (int, float)) and np.isinf(processed_value)):
                        processed_value = 0.0
                except (TypeError, ValueError):
                    # 如果无法检查无穷值，只检查NaN
                    if pd.isna(processed_value):
                        processed_value = 0.0
                
                processed_features[name] = processed_value
            
            return processed_features
            
        except Exception as e:
            logger.error(f"特征后处理失败: {e}")
            return features
    
    def _save_features_to_db(self, ts_code: str, trade_date: date, features: Dict[str, Any]):
        """保存特征到数据库"""
        try:
            feature_data_list = []
            
            for feature_name, feature_value in features.items():
                # 确定特征类别
                category = self._get_feature_category(feature_name)
                
                # 处理特征值，确保在合理范围内
                processed_value = self._process_feature_value(feature_value)
                
                feature_data = {
                    'ts_code': ts_code,
                    'trade_date': trade_date,
                    'feature_category': category,
                    'feature_name': feature_name,
                    'feature_value': processed_value,
                    'feature_metadata': {
                        'weight': self.feature_weights.get(category, 0.1),
                        'extracted_at': datetime.now().isoformat()
                    }
                }
                
                feature_data_list.append(feature_data)
            
            # 批量保存
            if feature_data_list:
                self.feature_dao.batch_create_feature_data(feature_data_list)
                logger.info(f"保存特征到数据库成功: {len(feature_data_list)}个特征")
            
        except Exception as e:
            logger.error(f"保存特征到数据库失败: {e}")
    
    def _process_feature_value(self, feature_value: Any) -> float:
        """处理特征值，确保在合理范围内"""
        try:
            # 如果是pandas Series或numpy数组，取最后一个值
            if hasattr(feature_value, 'iloc'):
                # pandas Series
                value = float(feature_value.iloc[-1]) if len(feature_value) > 0 else 0.0
            elif hasattr(feature_value, '__len__') and not isinstance(feature_value, str):
                # numpy数组或其他序列
                value = float(feature_value[-1]) if len(feature_value) > 0 else 0.0
            else:
                # 标量值
                value = float(feature_value)
            
            # 限制特征值范围，避免数据库溢出
            # DECIMAL(15, 8) 的范围大约是 -9999999.99999999 到 9999999.99999999
            max_value = 9999999.99999999
            min_value = -9999999.99999999
            
            if value > max_value:
                value = max_value
            elif value < min_value:
                value = min_value
            elif np.isnan(value) or np.isinf(value):
                value = 0.0
                
            return value
            
        except (ValueError, TypeError, IndexError) as e:
            logger.warning(f"处理特征值失败: {e}, 使用默认值0.0")
            return 0.0
    
    def _extract_moneyflow_features(self, df: pd.DataFrame, ts_code: str, trade_date: date) -> Dict[str, Any]:
        """
        提取资金流特征（使用历史数据，与其他特征保持一致）
        
        Args:
            df: 历史价格数据DataFrame，包含trade_date列
            ts_code: 股票代码
            trade_date: 当前交易日期
            
        Returns:
            资金流特征字典
        """
        try:
            # 从历史价格数据中提取日期范围（与其他特征保持一致）
            if df.empty or 'trade_date' not in df.columns:
                logger.warning(f"价格数据为空或缺少trade_date列，无法获取资金流数据: {ts_code} {trade_date}")
                return {}
            
            # 获取历史价格数据的日期范围（已在extract_all_features中统一限制，这里直接使用）
            df_dates = pd.to_datetime(df['trade_date']).dt.date
            start_date = df_dates.min()
            end_date = df_dates.max()  # 当前预测日期
            
            # 使用DatabaseManager获取session并查询资金流数据
            from dao.database import DatabaseManager
            db_manager = DatabaseManager()
            
            with db_manager.get_session() as session:
                moneyflow_dao = MoneyFlowDAO(session)
                
                # 获取该日期范围内的所有资金流数据（历史数据）
                moneyflow_data_list = moneyflow_dao.get_by_ts_code(ts_code, start_date, end_date)
                
                if not moneyflow_data_list:
                    logger.warning(f"未找到资金流数据: {ts_code} {start_date} 到 {end_date}")
                    return {}
                
                # 转换为DataFrame格式，按日期排序
                moneyflow_records = []
                for mf in moneyflow_data_list:
                    moneyflow_records.append({
                        'trade_date': mf.trade_date,
                        'buy_sm_amount': float(mf.buy_sm_amount) if mf.buy_sm_amount else 0.0,
                        'sell_sm_amount': float(mf.sell_sm_amount) if mf.sell_sm_amount else 0.0,
                        'buy_md_amount': float(mf.buy_md_amount) if mf.buy_md_amount else 0.0,
                        'sell_md_amount': float(mf.sell_md_amount) if mf.sell_md_amount else 0.0,
                        'buy_lg_amount': float(mf.buy_lg_amount) if mf.buy_lg_amount else 0.0,
                        'sell_lg_amount': float(mf.sell_lg_amount) if mf.sell_lg_amount else 0.0,
                        'buy_elg_amount': float(mf.buy_elg_amount) if mf.buy_elg_amount else 0.0,
                        'sell_elg_amount': float(mf.sell_elg_amount) if mf.sell_elg_amount else 0.0,
                        'net_mf_amount': float(mf.net_mf_amount) if mf.net_mf_amount else 0.0,
                        'net_mf_vol': float(mf.net_mf_vol) if mf.net_mf_vol else 0.0
                    })
                
                moneyflow_df = pd.DataFrame(moneyflow_records)
                moneyflow_df['trade_date'] = pd.to_datetime(moneyflow_df['trade_date'])
                moneyflow_df = moneyflow_df.sort_values('trade_date').reset_index(drop=True)
                
                # 提取资金流特征（传入历史资金流数据）
                return self.moneyflow_extractor.extract_all_features(df, moneyflow_df)
            
        except Exception as e:
            logger.error(f"提取资金流特征失败: {e}")
            return {}
    
    def _extract_active_features(self, ts_code: str, trade_date: date) -> Dict[str, Any]:
        """
        提取活跃特征（涨幅排名和涨幅阈值）
        
        Args:
            ts_code: 股票代码
            trade_date: 交易日期
            
        Returns:
            活跃特征字典，包含：
            - active_feature_1: 当日涨幅排名前10%（按主板、创业板、科创板区分），标记为1，其他标记为0
            - active_feature_2: 当日涨幅超过3%，标记为1，其他标记为0
        """
        try:
            # 使用DatabaseManager获取session并查询数据
            from dao.database import DatabaseManager
            db_manager = DatabaseManager()
            
            with db_manager.get_session() as session:
                daily_quote_dao = DailyQuoteDAO(session)
                stock_basic_dao = StockBasicDAO(session)
                
                # 获取当日所有股票的涨跌幅数据
                daily_quotes = daily_quote_dao.get_by_trade_date(trade_date)
                
                if not daily_quotes:
                    logger.warning(f"未找到当日涨跌幅数据: {trade_date}")
                    return {
                        'active_feature_1': 0.0,
                        'active_feature_2': 0.0
                    }
                
                # 转换为DataFrame
                daily_data = []
                for quote in daily_quotes:
                    if quote.pct_chg is not None:
                        try:
                            pct_chg_value = float(quote.pct_chg)
                            # 过滤掉 NaN 和无穷值
                            if not (pd.isna(pct_chg_value) or np.isinf(pct_chg_value)):
                                daily_data.append({
                                    'ts_code': quote.ts_code,
                                    'pct_chg': pct_chg_value
                                })
                        except (ValueError, TypeError) as e:
                            logger.debug(f"跳过无效的涨跌幅数据: {quote.ts_code} {quote.pct_chg} - {e}")
                            continue
                
                if not daily_data:
                    logger.warning(f"当日涨跌幅数据为空或无效: {trade_date}")
                    return {
                        'active_feature_1': 0.0,
                        'active_feature_2': 0.0
                    }
                
                daily_df = pd.DataFrame(daily_data)
                
                if daily_df.empty:
                    logger.warning(f"转换后的DataFrame为空: {trade_date}")
                    return {
                        'active_feature_1': 0.0,
                        'active_feature_2': 0.0
                    }
                
                # 获取所有股票的市场分类信息
                stock_basics = stock_basic_dao.get_all()
                stock_market_map = {}
                for stock in stock_basics:
                    if stock.market:
                        stock_market_map[stock.ts_code] = stock.market
                
                # 为每日数据添加市场分类
                daily_df['market'] = daily_df['ts_code'].map(stock_market_map)
                # 对于没有市场分类的股票，默认归类为主板
                daily_df['market'] = daily_df['market'].fillna('主板')
                
                # 过滤掉市场分类为空的股票（虽然已经填充，但保留此逻辑以防万一）
                daily_df = daily_df[daily_df['market'].notna()]
                
                # 找到当前股票的数据
                current_stock_data = daily_df[daily_df['ts_code'] == ts_code]
                
                if current_stock_data.empty:
                    logger.warning(f"未找到当前股票的当日数据: {ts_code} {trade_date}")
                    return {
                        'active_feature_1': 0.0,
                        'active_feature_2': 0.0
                    }
                
                current_pct_chg = float(current_stock_data.iloc[0]['pct_chg'])
                current_market = str(current_stock_data.iloc[0]['market'])
                
                # 验证数据有效性
                if pd.isna(current_pct_chg) or np.isinf(current_pct_chg):
                    logger.warning(f"当前股票涨跌幅数据无效: {ts_code} {trade_date} pct_chg={current_pct_chg}")
                    return {
                        'active_feature_1': 0.0,
                        'active_feature_2': 0.0
                    }
                
                # 计算活跃特征2：涨幅超过3%（注意：大于3%才标记为1，等于3%为0）
                active_feature_2 = 1.0 if current_pct_chg > 3.0 else 0.0
                
                # 计算活跃特征1：涨幅排名前10%（按市场类型分组）
                active_feature_1 = 0.0
                
                # 获取当前市场类型的所有股票
                market_stocks = daily_df[daily_df['market'] == current_market]
                
                if len(market_stocks) > 0:
                    # 按涨幅降序排序
                    market_stocks_sorted = market_stocks.sort_values('pct_chg', ascending=False)
                    
                    # 计算前10%的阈值（使用90分位数）
                    if len(market_stocks_sorted) > 0:
                        threshold_90 = float(market_stocks_sorted['pct_chg'].quantile(0.9))
                        
                        # 验证阈值有效性
                        if pd.isna(threshold_90) or np.isinf(threshold_90):
                            logger.warning(f"计算前10%阈值失败: 市场类型={current_market}, 股票数量={len(market_stocks_sorted)}")
                            active_feature_1 = 0.0
                        else:
                            # 如果当前股票的涨幅大于等于阈值，标记为1（包含边界值）
                            if current_pct_chg >= threshold_90:
                                active_feature_1 = 1.0
                                logger.debug(f"股票 {ts_code} 涨幅 {current_pct_chg:.2f}% 达到市场 {current_market} 前10%阈值 {threshold_90:.2f}%")
                            else:
                                active_feature_1 = 0.0
                    else:
                        logger.warning(f"市场类型 {current_market} 的股票数量为0")
                        active_feature_1 = 0.0
                else:
                    logger.warning(f"未找到市场类型 {current_market} 的股票数据，总股票数={len(daily_df)}")
                    active_feature_1 = 0.0
                
                features = {
                    'active_feature_1': float(active_feature_1),
                    'active_feature_2': float(active_feature_2)
                }
                
                logger.debug(f"提取活跃特征成功: {ts_code} {trade_date} - "
                           f"市场={current_market}, 涨幅={current_pct_chg:.2f}%, "
                           f"active_feature_1={active_feature_1}, active_feature_2={active_feature_2}")
                
                return features
            
        except Exception as e:
            logger.error(f"提取活跃特征失败: {ts_code} {trade_date} - {e}", exc_info=True)
            # 返回默认值
            return {
                'active_feature_1': 0.0,
                'active_feature_2': 0.0
            }
    
    def _get_feature_category(self, feature_name: str) -> str:
        """获取特征类别"""
        if feature_name.startswith('price_action_'):
            return 'price_action'
        elif feature_name.startswith('technical_'):
            return 'technical'
        elif feature_name.startswith('pattern_'):
            return 'pattern'
        elif feature_name.startswith('market_'):
            return 'market'
        elif feature_name.startswith('time_series_'):
            return 'time_series'
        elif feature_name.startswith('moneyflow_'):
            return 'moneyflow'
        else:
            return 'other'
    
    def get_features_for_prediction(self, ts_code: str, trade_date: date, 
                                  feature_categories: List[str] = None) -> Dict[str, float]:
        """获取用于预测的特征"""
        try:
            if feature_categories is None:
                feature_categories = ['price_action', 'technical', 'pattern', 'market']
            
            # 从数据库获取特征
            features = self.feature_dao.get_features_by_stock(
                ts_code, trade_date, feature_categories[0] if len(feature_categories) == 1 else None
            )
            
            # 转换为字典格式
            feature_dict = {}
            for feature in features:
                if feature.feature_category in feature_categories:
                    key = f"{feature.feature_category}_{feature.feature_name}"
                    feature_dict[key] = float(feature.feature_value) if feature.feature_value else 0.0
            
            logger.info(f"获取预测特征成功: {ts_code} {trade_date} - {len(feature_dict)}个特征")
            return feature_dict
            
        except Exception as e:
            logger.error(f"获取预测特征失败: {e}")
            return {}
    
    def get_feature_importance(self, model_name: str, model_version: str) -> Dict[str, float]:
        """获取特征重要性"""
        try:
            # 这里应该从模型性能表中获取特征重要性
            # 暂时返回空字典
            return {}
            
        except Exception as e:
            logger.error(f"获取特征重要性失败: {e}")
            return {}
    
    def get_feature_statistics(self, start_date: date = None, end_date: date = None) -> Dict[str, Any]:
        """获取特征统计信息"""
        try:
            return self.feature_dao.get_feature_statistics(start_date, end_date)
            
        except Exception as e:
            logger.error(f"获取特征统计信息失败: {e}")
            return {}
    
    def clean_old_features(self, days_to_keep: int = 365) -> int:
        """清理旧特征数据"""
        try:
            return self.feature_dao.delete_old_features(days_to_keep)
            
        except Exception as e:
            logger.error(f"清理旧特征数据失败: {e}")
            return 0
    
    def get_feature_matrix(self, ts_code: str, trade_date: date, 
                          feature_categories: List[str]) -> Dict[str, float]:
        """获取特征矩阵"""
        try:
            return self.feature_dao.get_feature_matrix(ts_code, trade_date, feature_categories)
            
        except Exception as e:
            logger.error(f"获取特征矩阵失败: {e}")
            return {}
    
    def validate_features(self, features: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """验证特征有效性"""
        try:
            errors = []
            
            # 检查特征数量
            if len(features) < 10:
                errors.append("特征数量不足")
            
            # 检查特征值
            for name, value in features.items():
                if pd.isna(value) or np.isinf(value):
                    errors.append(f"特征 {name} 值异常")
                elif isinstance(value, (int, float)) and abs(value) > 1e6:
                    errors.append(f"特征 {name} 值过大")
            
            # 检查特征类别
            categories = set()
            for name in features.keys():
                category = self._get_feature_category(name)
                categories.add(category)
            
            if len(categories) < 3:
                errors.append("特征类别不足")
            
            is_valid = len(errors) == 0
            return is_valid, errors
            
        except Exception as e:
            logger.error(f"验证特征失败: {e}")
            return False, [str(e)]
    
    def get_all_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        try:
            feature_names = []
            
            # 价格行为特征
            price_action_names = self.price_action_extractor.get_feature_names()
            feature_names.extend([f"price_action_{name}" for name in price_action_names])
            
            # 技术指标特征
            technical_names = self.technical_extractor.get_feature_names()
            feature_names.extend([f"technical_{name}" for name in technical_names])
            
            # 形态识别特征
            pattern_names = self.pattern_extractor.get_feature_names()
            feature_names.extend([f"pattern_{name}" for name in pattern_names])
            
            # 市场特征
            market_names = self.market_extractor.get_feature_names()
            feature_names.extend([f"market_{name}" for name in market_names])
            
            # 时间序列特征
            time_series_names = self.time_series_extractor.get_feature_names()
            feature_names.extend([f"time_series_{name}" for name in time_series_names])
            
            # 资金流特征
            moneyflow_names = self.moneyflow_extractor.get_feature_names()
            feature_names.extend([f"moneyflow_{name}" for name in moneyflow_names])
            
            return feature_names
            
        except Exception as e:
            logger.error(f"获取特征名称失败: {e}")
            return []
    
    def get_feature_categories(self) -> List[str]:
        """获取特征类别列表"""
        return list(self.feature_weights.keys())
    
    def get_feature_weights(self) -> Dict[str, float]:
        """获取特征权重"""
        return self.feature_weights.copy()
    
    def update_feature_weights(self, weights: Dict[str, float]):
        """更新特征权重"""
        try:
            # 验证权重
            total_weight = sum(weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"特征权重总和不为1: {total_weight}")
            
            self.feature_weights.update(weights)
            logger.info(f"更新特征权重成功: {weights}")
            
        except Exception as e:
            logger.error(f"更新特征权重失败: {e}")
