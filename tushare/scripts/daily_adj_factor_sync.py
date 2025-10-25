#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
复权因子日常数据同步脚本
用于每日同步复权因子数据
"""

import sys
import os
from datetime import datetime, date, timedelta
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from dao.database import DatabaseManager
from services.adj_factor_service import AdjFactorService
from services.trade_cal_service import TradeCalService

logger = setup_logger()

class DailyAdjFactorSync:
    """复权因子日常数据同步器"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.adj_factor_service = AdjFactorService()
        self.trade_cal_service = TradeCalService()
    
    def sync_today_data(self) -> Dict[str, Any]:
        """
        同步当日复权因子数据
        
        Returns:
            同步结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            logger.info("开始同步当日复权因子数据...")
            
            with self.db.get_session() as session:
                # 同步当日数据
                count = self.adj_factor_service.sync_today_data(session)
                
                stats.update({
                    'sync_type': 'today',
                    'records_count': count,
                    'sync_date': datetime.now().strftime('%Y-%m-%d')
                })
                
                if count > 0:
                    logger.info(f"当日复权因子数据同步成功，共 {count} 条记录")
                else:
                    logger.warning("当日复权因子数据为空或已存在")
                
        except Exception as e:
            logger.error(f"同步当日复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def sync_last_trading_day_data(self) -> Dict[str, Any]:
        """
        同步上一交易日复权因子数据
        
        Returns:
            同步结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            logger.info("开始同步上一交易日复权因子数据...")
            
            with self.db.get_session() as session:
                # 同步上一交易日数据
                count = self.adj_factor_service.sync_daily_data_optimized(session)
                
                stats.update({
                    'sync_type': 'last_trading_day',
                    'records_count': count
                })
                
                if count > 0:
                    logger.info(f"上一交易日复权因子数据同步成功，共 {count} 条记录")
                else:
                    logger.warning("上一交易日复权因子数据为空或已存在")
                
        except Exception as e:
            logger.error(f"同步上一交易日复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def sync_specific_date_data(self, trade_date: str) -> Dict[str, Any]:
        """
        同步指定日期的复权因子数据
        
        Args:
            trade_date: 交易日期 YYYYMMDD
            
        Returns:
            同步结果统计
        """
        start_time = datetime.now()
        stats = {'success': True, 'start_time': start_time}
        
        try:
            logger.info(f"开始同步指定日期复权因子数据: {trade_date}")
            
            with self.db.get_session() as session:
                # 同步指定日期数据
                count = self.adj_factor_service.sync_daily_data(session, trade_date)
                
                stats.update({
                    'sync_type': 'specific_date',
                    'records_count': count,
                    'sync_date': trade_date
                })
                
                if count > 0:
                    logger.info(f"指定日期复权因子数据同步成功，共 {count} 条记录")
                else:
                    logger.warning(f"指定日期 {trade_date} 复权因子数据为空或已存在")
                
        except Exception as e:
            logger.error(f"同步指定日期复权因子数据失败: {e}")
            stats['success'] = False
            stats['error'] = str(e)
        finally:
            stats['duration'] = (datetime.now() - start_time).total_seconds()
        
        return stats
    
    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态信息"""
        try:
            with self.db.get_session() as session:
                return self.adj_factor_service.get_sync_progress(session)
        except Exception as e:
            logger.error(f"获取复权因子同步状态失败: {e}")
            return {'error': str(e)}


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='复权因子日常数据同步工具')
    parser.add_argument('--mode', choices=['today', 'last', 'specific'], default='last',
                       help='同步模式：today=当日数据，last=上一交易日，specific=指定日期')
    parser.add_argument('--date', 
                       help='指定日期 YYYYMMDD（仅specific模式有效）')
    parser.add_argument('--status', action='store_true',
                       help='显示同步状态信息')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    sync_manager = DailyAdjFactorSync()
    
    try:
        if args.status:
            # 显示同步状态
            status = sync_manager.get_sync_status()
            print("复权因子数据同步状态:")
            print(f"  总记录数: {status.get('total_records', 0)}")
            print(f"  股票数量: {status.get('stock_count', 0)}")
            print(f"  日期范围: {status.get('date_range', {})}")
            print(f"  最后更新: {status.get('last_updated', '未知')}")
            return
        
        if args.mode == 'today':
            # 同步当日数据
            logger.info("执行当日复权因子数据同步...")
            result = sync_manager.sync_today_data()
            
        elif args.mode == 'last':
            # 同步上一交易日数据
            logger.info("执行上一交易日复权因子数据同步...")
            result = sync_manager.sync_last_trading_day_data()
            
        elif args.mode == 'specific':
            # 同步指定日期数据
            if not args.date:
                logger.error("指定日期模式需要提供 --date 参数")
                return
            
            logger.info(f"执行指定日期复权因子数据同步: {args.date}")
            result = sync_manager.sync_specific_date_data(args.date)
        
        # 输出结果
        if result['success']:
            logger.info("复权因子数据同步成功完成")
            logger.info(f"  同步类型: {result.get('sync_type', '未知')}")
            logger.info(f"  记录数量: {result.get('records_count', 0)}")
            logger.info(f"  耗时: {result.get('duration', 0):.2f} 秒")
        else:
            logger.error(f"复权因子数据同步失败: {result.get('error', '未知错误')}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
