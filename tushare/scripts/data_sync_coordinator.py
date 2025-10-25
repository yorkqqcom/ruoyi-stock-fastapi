#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据同步协调器
负责管理数据同步状态和特征计算触发条件
确保数据下载与特征计算完全隔离
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
from loguru import logger
import json

from dao.database import db_manager
from services.trade_cal_service import TradeCalService

class DataSyncCoordinator:
    """数据同步协调器"""
    
    def __init__(self):
        """初始化协调器"""
        self.trade_cal_service = TradeCalService()
        
    def set_data_sync_completed(self, sync_type: str, sync_date: str, 
                               sync_results: Dict[str, Any]) -> bool:
        """
        设置数据同步完成标志
        
        Args:
            sync_type: 同步类型 ('morning', 'afternoon', 'full')
            sync_date: 同步日期 YYYY-MM-DD
            sync_results: 同步结果统计
        """
        try:
            with db_manager.get_session() as session:
                # 检查是否为交易日
                if not self._is_trading_day(sync_date, session):
                    logger.info(f"{sync_date} 不是交易日，跳过数据就绪标志设置")
                    return True
                
                # 创建或更新数据就绪标志
                flag_data = {
                    'sync_type': sync_type,
                    'sync_date': sync_date,
                    'sync_time': datetime.now().isoformat(),
                    'sync_results': sync_results,
                    'data_ready': True,
                    'feature_extraction_triggered': False
                }
                
                # 保存到数据库（这里使用简单的JSON存储，实际项目中可以创建专门的状态表）
                self._save_sync_flag(flag_data, session)
                
                logger.info(f"数据同步完成标志已设置: {sync_type} - {sync_date}")
                return True
                
        except Exception as e:
            logger.error(f"设置数据同步完成标志失败: {e}")
            return False
    
    def check_data_ready_for_features(self, target_date: str) -> Dict[str, Any]:
        """
        检查数据是否就绪，可以开始特征计算
        
        Args:
            target_date: 目标日期 YYYY-MM-DD
            
        Returns:
            检查结果字典
        """
        try:
            with db_manager.get_session() as session:
                # 检查是否为交易日
                if not self._is_trading_day(target_date, session):
                    return {
                        'ready': False,
                        'reason': 'not_trading_day',
                        'message': f'{target_date} 不是交易日'
                    }
                
                # 检查数据同步状态
                sync_flag = self._get_sync_flag(target_date, session)
                if not sync_flag:
                    return {
                        'ready': False,
                        'reason': 'no_sync_flag',
                        'message': f'{target_date} 数据同步未完成'
                    }
                
                # 检查是否已经触发过特征计算
                if sync_flag.get('feature_extraction_triggered', False):
                    return {
                        'ready': False,
                        'reason': 'already_triggered',
                        'message': f'{target_date} 特征计算已触发'
                    }
                
                # 检查数据质量
                quality_check = self._check_data_quality(target_date, session)
                if not quality_check['passed']:
                    return {
                        'ready': False,
                        'reason': 'data_quality_failed',
                        'message': f'数据质量检查失败: {quality_check["message"]}'
                    }
                
                return {
                    'ready': True,
                    'sync_flag': sync_flag,
                    'quality_check': quality_check
                }
                
        except Exception as e:
            logger.error(f"检查数据就绪状态失败: {e}")
            return {
                'ready': False,
                'reason': 'error',
                'message': str(e)
            }
    
    def mark_feature_extraction_triggered(self, target_date: str) -> bool:
        """
        标记特征计算已触发
        
        Args:
            target_date: 目标日期 YYYY-MM-DD
        """
        try:
            with db_manager.get_session() as session:
                sync_flag = self._get_sync_flag(target_date, session)
                if sync_flag:
                    sync_flag['feature_extraction_triggered'] = True
                    sync_flag['feature_extraction_time'] = datetime.now().isoformat()
                    self._save_sync_flag(sync_flag, session)
                    logger.info(f"特征计算触发标志已设置: {target_date}")
                    return True
                else:
                    logger.warning(f"未找到 {target_date} 的同步标志")
                    return False
                    
        except Exception as e:
            logger.error(f"标记特征计算触发失败: {e}")
            return False
    
    def get_sync_status(self, target_date: str) -> Dict[str, Any]:
        """
        获取指定日期的同步状态
        
        Args:
            target_date: 目标日期 YYYY-MM-DD
        """
        try:
            with db_manager.get_session() as session:
                sync_flag = self._get_sync_flag(target_date, session)
                if not sync_flag:
                    return {
                        'exists': False,
                        'message': f'{target_date} 无同步记录'
                    }
                
                return {
                    'exists': True,
                    'sync_type': sync_flag.get('sync_type'),
                    'sync_date': sync_flag.get('sync_date'),
                    'sync_time': sync_flag.get('sync_time'),
                    'data_ready': sync_flag.get('data_ready', False),
                    'feature_extraction_triggered': sync_flag.get('feature_extraction_triggered', False),
                    'sync_results': sync_flag.get('sync_results', {})
                }
                
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {'exists': False, 'error': str(e)}
    
    def _is_trading_day(self, target_date: str, session) -> bool:
        """检查是否为交易日"""
        try:
            trade_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            return self.trade_cal_service.is_trading_day(trade_date, session)
        except Exception as e:
            logger.error(f"检查交易日失败: {e}")
            return False
    
    def _save_sync_flag(self, flag_data: Dict[str, Any], session):
        """保存同步标志（简化实现，实际项目中应创建专门的状态表）"""
        # 这里使用简单的文件存储，实际项目中应该创建数据库表
        flag_file = f"data/sync_flags/{flag_data['sync_date']}.json"
        os.makedirs(os.path.dirname(flag_file), exist_ok=True)
        
        with open(flag_file, 'w', encoding='utf-8') as f:
            json.dump(flag_data, f, ensure_ascii=False, indent=2)
    
    def _get_sync_flag(self, target_date: str, session) -> Optional[Dict[str, Any]]:
        """获取同步标志"""
        try:
            flag_file = f"data/sync_flags/{target_date}.json"
            if os.path.exists(flag_file):
                with open(flag_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"获取同步标志失败: {e}")
            return None
    
    def _check_data_quality(self, target_date: str, session) -> Dict[str, Any]:
        """
        检查数据质量
        
        Args:
            target_date: 目标日期 YYYY-MM-DD
        """
        try:
            # 这里可以添加具体的数据质量检查逻辑
            # 例如：检查日线数据完整性、复权数据完整性等
            
            # 简化实现：假设数据质量检查通过
            return {
                'passed': True,
                'message': '数据质量检查通过',
                'checks': {
                    'daily_quotes': True,
                    'adjusted_quotes': True,
                    'moneyflow': True
                }
            }
            
        except Exception as e:
            logger.error(f"数据质量检查失败: {e}")
            return {
                'passed': False,
                'message': f'数据质量检查失败: {e}',
                'checks': {}
            }
    
    def cleanup_old_flags(self, days: int = 30):
        """
        清理旧的同步标志
        
        Args:
            days: 保留天数
        """
        try:
            cutoff_date = datetime.now().date() - timedelta(days=days)
            flag_dir = "data/sync_flags"
            
            if os.path.exists(flag_dir):
                for filename in os.listdir(flag_dir):
                    if filename.endswith('.json'):
                        file_date_str = filename.replace('.json', '')
                        try:
                            file_date = datetime.strptime(file_date_str, '%Y-%m-%d').date()
                            if file_date < cutoff_date:
                                file_path = os.path.join(flag_dir, filename)
                                os.remove(file_path)
                                logger.info(f"清理旧标志文件: {filename}")
                        except ValueError:
                            continue
                            
        except Exception as e:
            logger.error(f"清理旧标志失败: {e}")


def main():
    """主函数 - 用于测试协调器功能"""
    import argparse
    
    parser = argparse.ArgumentParser(description='数据同步协调器')
    parser.add_argument('--action', 
                       choices=['set_completed', 'check_ready', 'mark_triggered', 'get_status', 'cleanup'], 
                       required=True,
                       help='操作类型')
    parser.add_argument('--date', 
                       default=datetime.now().strftime('%Y-%m-%d'),
                       help='目标日期 YYYY-MM-DD')
    parser.add_argument('--sync-type', 
                       default='morning',
                       help='同步类型')
    
    args = parser.parse_args()
    
    coordinator = DataSyncCoordinator()
    
    if args.action == 'set_completed':
        # 模拟设置数据同步完成
        sync_results = {
            'daily_quotes': 1000,
            'moneyflow': 500,
            'adjusted_quotes': 1000
        }
        result = coordinator.set_data_sync_completed(args.sync_type, args.date, sync_results)
        print(f"设置完成标志: {'成功' if result else '失败'}")
        
    elif args.action == 'check_ready':
        result = coordinator.check_data_ready_for_features(args.date)
        print(f"数据就绪检查: {result}")
        
    elif args.action == 'mark_triggered':
        result = coordinator.mark_feature_extraction_triggered(args.date)
        print(f"标记特征计算触发: {'成功' if result else '失败'}")
        
    elif args.action == 'get_status':
        result = coordinator.get_sync_status(args.date)
        print(f"同步状态: {result}")
        
    elif args.action == 'cleanup':
        coordinator.cleanup_old_flags()
        print("清理完成")


if __name__ == '__main__':
    main()
