#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DailyDataSync
封装日常与全量数据同步流程，供调度器与独立脚本调用。
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from dao.database import DatabaseManager
from services.trade_cal_service import TradeCalService
from services.stock_basic_service import StockBasicService
from services.daily_quote_service import DailyQuoteService
from services.moneyflow_service import MoneyFlowService
from services.adjusted_quote_service import AdjustedQuoteService

logger = setup_logger()

class DailyDataSync:
    """日常数据同步管理器"""

    def __init__(self):
        self.db = DatabaseManager()
        self.trade_cal_service = TradeCalService()
        self.stock_basic_service = StockBasicService()
        self.daily_quote_service = DailyQuoteService()
        self.moneyflow_service = MoneyFlowService()
        self.adjusted_quote_service = AdjustedQuoteService()

    def run_full_sync(self, use_today: bool = False) -> Dict[str, Any]:
        """全量/常规日同步：交易日历、基础信息、日线、资金流、复权"""
        start = datetime.now()
        stats: Dict[str, Any] = { 'success': True }
        try:
            with self.db.get_session() as session:
                # 交易日历（近3年）
                cal_count = self.trade_cal_service.sync_recent_trade_cal(years=3, session=session)
                # 股票基础信息（全量）
                stock_count = self.stock_basic_service.sync_all_stock_basic(session)
                
                # 根据参数选择同步模式
                if use_today:
                    # 日线（当日）
                    daily_count = self.daily_quote_service.sync_today_data(session)
                    # 资金流（当日）
                    moneyflow_count = self.moneyflow_service.sync_today_data(session)
                    # 复权（当日，qfq/hfq/none）
                    adj_count = self.adjusted_quote_service.sync_today_data(session)
                else:
                    # 日线（上个交易日）
                    daily_count = self.daily_quote_service.sync_daily_data_optimized(session)
                    # 资金流（上个交易日）
                    moneyflow_count = self.moneyflow_service.sync_daily_data_optimized(session)
                    # 复权（上个交易日，qfq/hfq/none）
                    adj_count = self.adjusted_quote_service.sync_daily_data_optimized(session)

                stats.update({
                    'trade_cal': cal_count,
                    'stock_basic': stock_count,
                    'daily_quotes': daily_count,
                    'moneyflow': moneyflow_count,
                    'adjusted_quotes': adj_count,
                })
        except Exception as e:
            logger.error(f"全量同步失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start).total_seconds()
        return stats

    def run_quick_sync(self, use_today: bool = False) -> Dict[str, Any]:
        """快速同步：仅日线、资金流、复权"""
        start = datetime.now()
        stats: Dict[str, Any] = { 'success': True }
        try:
            with self.db.get_session() as session:
                if use_today:
                    # 当日数据
                    daily_count = self.daily_quote_service.sync_today_data(session)
                    moneyflow_count = self.moneyflow_service.sync_today_data(session)
                    adj_count = self.adjusted_quote_service.sync_today_data(session)
                else:
                    # 上个交易日数据
                    daily_count = self.daily_quote_service.sync_daily_data_optimized(session)
                    moneyflow_count = self.moneyflow_service.sync_daily_data_optimized(session)
                    adj_count = self.adjusted_quote_service.sync_daily_data_optimized(session)
                
                stats.update({
                    'daily_quotes': daily_count,
                    'moneyflow': moneyflow_count,
                    'adjusted_quotes': adj_count,
                })
        except Exception as e:
            logger.error(f"快速同步失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start).total_seconds()
        return stats

    def get_sync_statistics(self, session) -> Dict[str, Any]:
        """获取各模块同步统计"""
        try:
            trade_cal_stats = self.trade_cal_service.get_trade_cal_statistics(session)
            daily_stats = self.daily_quote_service.get_sync_progress(session)
            moneyflow_stats = self.moneyflow_service.get_sync_progress(session)
            adjusted_stats = self.adjusted_quote_service.get_sync_progress(session)
            return {
                'trade_cal': trade_cal_stats,
                'daily_quotes': daily_stats,
                'moneyflow': moneyflow_stats,
                'adjusted_quotes': adjusted_stats,
            }
        except Exception as e:
            logger.error(f"获取同步统计失败: {e}")
            return {'error': str(e)}


def main():
    import argparse
    parser = argparse.ArgumentParser(description='日常数据同步工具')
    parser.add_argument('--mode', choices=['full', 'quick'], default='full',
                       help='同步模式：full=全量同步，quick=快速同步')
    parser.add_argument('--today', action='store_true',
                       help='同步当日数据（默认为上一交易日）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    args = parser.parse_args()

    # 设置日志级别
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")

    syncer = DailyDataSync()
    
    if args.mode == 'full':
        res = syncer.run_full_sync(use_today=args.today)
    else:
        res = syncer.run_quick_sync(use_today=args.today)
    
    # 输出结果
    if args.today:
        print(f"[当日数据同步] 模式: {args.mode}, 结果: {res}")
    else:
        print(f"[上一交易日数据同步] 模式: {args.mode}, 结果: {res}")


if __name__ == '__main__':
    main()
