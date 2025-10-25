#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权因子数据初始化脚本
用于初始化历史复权因子数据
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from dao.database import DatabaseManager
from dao.stock_basic_dao import StockBasicDAO
from services.adj_factor_service import AdjFactorService
from services.trade_cal_service import TradeCalService

logger = setup_logger()

class AdjFactorInitializer:
    """复权因子数据初始化器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.adj_factor_service = AdjFactorService()
        self.trade_cal_service = TradeCalService()
    
    def init_all_stocks(self, start_date: str = '20140101', end_date: str = None) -> Dict[str, Any]:
        """
        初始化所有股票的历史复权因子数据
        
        Args:
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            
        Returns:
            初始化结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            with self.db.get_session() as session:
                # 1. 确保交易日历已同步
                logger.info("检查交易日历数据...")
                cal_count = self.trade_cal_service.sync_recent_trade_cal(years=3, session=session)
                logger.info(f"交易日历同步完成，共 {cal_count} 条记录")
                
                # 2. 获取所有股票列表
                logger.info("获取股票列表...")
                stock_basic_dao = StockBasicDAO(session)
                stocks = stock_basic_dao.get_all()
                
                if not stocks:
                    logger.warning("未找到股票列表，请先同步股票基础信息")
                    stats['success'] = False
                    stats['error'] = "未找到股票列表"
                    return stats
                
                ts_codes = [stock.ts_code for stock in stocks]
                logger.info(f"找到 {len(ts_codes)} 只股票，开始同步复权因子数据")
                
                # 3. 批量同步复权因子数据
                total_count = self.adj_factor_service.sync_historical_data_batch(
                    session, ts_codes, start_date, end_date
                )
                
                stats.update({
                    'stock_count': len(ts_codes),
                    'total_records': total_count,
                    'start_date': start_date,
                    'end_date': end_date or datetime.now().strftime('%Y%m%d')
                })
                
        except Exception as e:
            logger.error(f"初始化复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def init_specific_stocks(self, ts_codes: List[str], start_date: str = '20140101', 
                           end_date: str = None) -> Dict[str, Any]:
        """
        初始化指定股票的历史复权因子数据
        
        Args:
            ts_codes: 股票代码列表
            start_date: 开始日期 YYYYMMDD
            end_date: 结束日期 YYYYMMDD
            
        Returns:
            初始化结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            with self.db.get_session() as session:
                logger.info(f"开始初始化 {len(ts_codes)} 只股票的复权因子数据")
                
                # 批量同步指定股票的复权因子数据
                total_count = self.adj_factor_service.sync_historical_data_batch(
                    session, ts_codes, start_date, end_date
                )
                
                stats.update({
                    'stock_count': len(ts_codes),
                    'total_records': total_count,
                    'start_date': start_date,
                    'end_date': end_date or datetime.now().strftime('%Y%m%d')
                })
                
        except Exception as e:
            logger.error(f"初始化指定股票复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def init_recent_data(self, days: int = 30) -> Dict[str, Any]:
        """
        初始化最近N天的复权因子数据
        
        Args:
            days: 最近天数
            
        Returns:
            初始化结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            # 计算日期范围
            end_date = datetime.now().strftime('%Y%m%d')
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')
            
            logger.info(f"初始化最近 {days} 天的复权因子数据: {start_date} 到 {end_date}")
            
            with self.db.get_session() as session:
                # 获取所有股票列表
                stock_basic_dao = StockBasicDAO(session)
                stocks = stock_basic_dao.get_all()
                
                if not stocks:
                    logger.warning("未找到股票列表，请先同步股票基础信息")
                    stats['success'] = False
                    stats['error'] = "未找到股票列表"
                    return stats
                
                ts_codes = [stock.ts_code for stock in stocks]
                
                # 批量同步最近数据
                total_count = self.adj_factor_service.sync_historical_data_batch(
                    session, ts_codes, start_date, end_date
                )
                
                stats.update({
                    'stock_count': len(ts_codes),
                    'total_records': total_count,
                    'start_date': start_date,
                    'end_date': end_date,
                    'days': days
                })
                
        except Exception as e:
            logger.error(f"初始化最近复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取复权因子数据统计信息"""
        try:
            with self.db.get_session() as session:
                return self.adj_factor_service.get_sync_progress(session)
        except Exception as e:
            logger.error(f"获取复权因子统计信息失败: {e}")
            return {'error': str(e)}


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='复权因子数据初始化工具')
    parser.add_argument('--mode', choices=['all', 'recent', 'specific'], default='recent',
                       help='初始化模式：all=全部历史数据，recent=最近数据，specific=指定股票')
    parser.add_argument('--start-date', default='20140101',
                       help='开始日期 YYYYMMDD')
    parser.add_argument('--end-date', 
                       help='结束日期 YYYYMMDD')
    parser.add_argument('--days', type=int, default=30,
                       help='最近天数（仅recent模式有效）')
    parser.add_argument('--stocks', 
                       help='指定股票代码，逗号分隔（仅specific模式有效）')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    parser.add_argument('--stats', action='store_true',
                       help='显示统计信息')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    initializer = AdjFactorInitializer()
    
    try:
        if args.stats:
            # 显示统计信息
            stats = initializer.get_statistics()
            print("复权因子数据统计信息:")
            print(f"  总记录数: {stats.get('total_records', 0)}")
            print(f"  股票数量: {stats.get('stock_count', 0)}")
            print(f"  日期范围: {stats.get('date_range', {})}")
            print(f"  最后更新: {stats.get('last_updated', '未知')}")
            return
        
        if args.mode == 'all':
            # 初始化全部历史数据
            logger.info("开始初始化全部历史复权因子数据...")
            result = initializer.init_all_stocks(args.start_date, args.end_date)
            
        elif args.mode == 'recent':
            # 初始化最近数据
            logger.info(f"开始初始化最近 {args.days} 天的复权因子数据...")
            result = initializer.init_recent_data(args.days)
            
        elif args.mode == 'specific':
            # 初始化指定股票数据
            if not args.stocks:
                logger.error("指定股票模式需要提供 --stocks 参数")
                return
            
            ts_codes = [code.strip() for code in args.stocks.split(',')]
            logger.info(f"开始初始化指定股票的复权因子数据: {ts_codes}")
            result = initializer.init_specific_stocks(ts_codes, args.start_date, args.end_date)
        
        # 输出结果
        if result['success']:
            logger.info("复权因子数据初始化成功完成")
            logger.info(f"  股票数量: {result.get('stock_count', 0)}")
            logger.info(f"  记录数量: {result.get('total_records', 0)}")
            logger.info(f"  耗时: {result.get('duration', 0):.2f} 秒")
        else:
            logger.error(f"复权因子数据初始化失败: {result.get('error', '未知错误')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
