#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版定时任务调度器
用于股票预测系统的定时数据同步
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import schedule
import time
import threading
from datetime import datetime, timedelta
from loguru import logger
from scripts.daily_data_sync import DailyDataSync
from scripts.step1_extract_and_save_features import FeatureExtractor
from scripts.data_sync_coordinator import DataSyncCoordinator

class EnhancedScheduler:
    """增强版任务调度器"""
    
    def __init__(self):
        """初始化调度器"""
        self.running = False
        self.sync_manager = DailyDataSync()
        self.feature_extractor = FeatureExtractor()
        self.coordinator = DataSyncCoordinator()
        self.setup_jobs()
        self.job_history = []
        
    def setup_jobs(self):
        """设置定时任务"""
        # 每天早上8:30 - 完整数据同步
        schedule.every().day.at("08:30").do(self.run_morning_sync)
        
        # 每天下午18:30 - 快速数据同步（收盘后）
        schedule.every().day.at("18:30").do(self.run_afternoon_sync)
        
        # 每天晚上23:00 - 特征提取
        schedule.every().day.at("23:00").do(self.run_feature_extraction)
        
        # 每天晚上21:00 - 数据统计报告
        # schedule.every().day.at("5:00").do(self.run_statistics_report)
        
        # 每周一早上7:00 - 完整特征重新计算
        # schedule.every().monday.at("07:00").do(self.run_weekly_feature_rebuild)
        
        # 每周日晚上22:00 - 系统维护
        schedule.every().sunday.at("22:00").do(self.run_weekly_maintenance)
        
        logger.info("增强版定时任务设置完成")
        self._log_scheduled_jobs()
    
    def _log_scheduled_jobs(self):
        """记录已设置的任务"""
        jobs = schedule.get_jobs()
        logger.info(f"已设置 {len(jobs)} 个定时任务:")
        for job in jobs:
            logger.info(f"  - {job}")
    
    def run_morning_sync(self):
        """执行早晨数据同步"""
        job_name = "早晨数据同步"
        start_time = datetime.now()
        sync_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            logger.info(f"开始执行 {job_name}")
            results = self.sync_manager.run_full_sync()
            
            # 设置数据同步完成标志
            if results['success']:
                self.coordinator.set_data_sync_completed(
                    sync_type='morning',
                    sync_date=sync_date,
                    sync_results=results
                )
                logger.info(f"数据同步完成标志已设置: {sync_date}")
            
            # 记录任务历史
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': results['success'],
                'duration': results['duration']
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def run_afternoon_sync(self):
        """执行下午快速同步"""
        job_name = "下午快速同步"
        start_time = datetime.now()
        sync_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            logger.info(f"开始执行 {job_name}")
            results = self.sync_manager.run_quick_sync()
            
            # 设置数据同步完成标志
            if results['success']:
                self.coordinator.set_data_sync_completed(
                    sync_type='afternoon',
                    sync_date=sync_date,
                    sync_results=results
                )
                logger.info(f"数据同步完成标志已设置: {sync_date}")
            
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': results['success'],
                'duration': results['duration']
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def run_feature_extraction(self):
        """执行特征提取（带数据就绪检查）"""
        job_name = "特征提取"
        start_time = datetime.now()
        target_date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            logger.info(f"开始执行 {job_name}")
            
            # 检查数据是否就绪
            ready_check = self.coordinator.check_data_ready_for_features(target_date)
            if not ready_check['ready']:
                logger.warning(f"数据未就绪，跳过特征提取: {ready_check['message']}")
                self.job_history.append({
                    'name': job_name,
                    'start_time': start_time,
                    'end_time': datetime.now(),
                    'success': False,
                    'reason': ready_check['reason'],
                    'message': ready_check['message']
                })
                return
            
            # 标记特征计算已触发
            self.coordinator.mark_feature_extraction_triggered(target_date)
            
            # 获取最近3天的数据范围（日常特征提取）
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=3)
            
            # 执行特征提取
            results = self.feature_extractor.extract_features_batch(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                max_stocks=100,  # 限制数量避免过载
                adj_type='qfq'
            )
            
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': True,
                'results': results
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def run_statistics_report(self):
        """执行统计报告"""
        job_name = "统计报告"
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行 {job_name}")
            
            # 生成统计报告
            from dao.database import db_manager
            with db_manager.get_session() as session:
                stats = self.sync_manager.get_sync_statistics(session)
                
                logger.info("=" * 50)
                logger.info("每日数据统计报告")
                logger.info("=" * 50)
                logger.info(f"报告时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info("")
                
                # 股票基础信息统计
                if 'stock_basic' in stats:
                    stock_stats = stats['stock_basic']
                    logger.info("股票基础信息:")
                    logger.info(f"  总股票数: {stock_stats.get('total_stocks', 0)}")
                    logger.info(f"  正常上市: {stock_stats.get('active_stocks', 0)}")
                    logger.info(f"  已退市: {stock_stats.get('delisted_stocks', 0)}")
                    logger.info(f"  暂停上市: {stock_stats.get('suspended_stocks', 0)}")
                
                # 日线行情统计
                if 'daily_quotes' in stats:
                    daily_stats = stats['daily_quotes']
                    logger.info("日线行情数据:")
                    logger.info(f"  总记录数: {daily_stats.get('total_records', 0)}")
                    logger.info(f"  最新日期: {daily_stats.get('latest_date', '未知')}")
                
                # 资金流向统计
                if 'moneyflow' in stats:
                    moneyflow_stats = stats['moneyflow']
                    logger.info("资金流向数据:")
                    logger.info(f"  总记录数: {moneyflow_stats.get('total_records', 0)}")
                    logger.info(f"  最新日期: {moneyflow_stats.get('latest_date', '未知')}")
                
                logger.info("=" * 50)
            
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': True
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def run_weekly_feature_rebuild(self):
        """执行周度特征重建"""
        job_name = "周度特征重建"
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行 {job_name}")
            
            # 获取最近30天的数据范围
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
            
            # 执行完整特征提取
            results = self.feature_extractor.extract_features_batch(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                max_stocks=500,  # 周度重建处理更多股票
                adj_type='qfq'
            )
            
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': True,
                'results': results
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def run_weekly_maintenance(self):
        """执行周度系统维护"""
        job_name = "周度系统维护"
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行 {job_name}")
            
            # 清理旧日志文件
            self._cleanup_old_logs()
            
            # 数据库维护
            self._database_maintenance()
            
            # 清理任务历史（保留最近30天）
            self._cleanup_job_history()
            
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': True
            })
            
            logger.info(f"{job_name} 执行完成")
            
        except Exception as e:
            logger.error(f"{job_name} 执行失败: {e}")
            self.job_history.append({
                'name': job_name,
                'start_time': start_time,
                'end_time': datetime.now(),
                'success': False,
                'error': str(e)
            })
    
    def _cleanup_old_logs(self):
        """清理旧日志文件"""
        try:
            import glob
            import os
            
            log_dir = "logs"
            if os.path.exists(log_dir):
                # 删除7天前的日志文件
                cutoff_date = datetime.now() - timedelta(days=7)
                
                for log_file in glob.glob(os.path.join(log_dir, "*.log.*")):
                    file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
                    if file_time < cutoff_date:
                        os.remove(log_file)
                        logger.info(f"删除旧日志文件: {log_file}")
            
        except Exception as e:
            logger.warning(f"清理日志文件失败: {e}")
    
    def _database_maintenance(self):
        """数据库维护"""
        try:
            from dao.database import db_manager
            
            with db_manager.get_session() as session:
                # 这里可以添加数据库优化操作
                # 例如：重建索引、清理临时表等
                logger.info("数据库维护完成")
                
        except Exception as e:
            logger.warning(f"数据库维护失败: {e}")
    
    def _cleanup_job_history(self):
        """清理任务历史"""
        try:
            # 保留最近30天的任务历史
            cutoff_date = datetime.now() - timedelta(days=30)
            self.job_history = [
                job for job in self.job_history 
                if job['start_time'] > cutoff_date
            ]
            logger.info(f"任务历史清理完成，保留 {len(self.job_history)} 条记录")
            
        except Exception as e:
            logger.warning(f"清理任务历史失败: {e}")
    
    def start(self):
        """启动调度器"""
        self.running = True
        logger.info("增强版任务调度器启动")
        logger.info(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("接收到停止信号，正在关闭调度器...")
            self.stop()
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("增强版任务调度器停止")
    
    def get_job_history(self, days: int = 7):
        """获取任务历史"""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_jobs = [
            job for job in self.job_history 
            if job['start_time'] > cutoff_date
        ]
        return recent_jobs
    
    def get_status(self):
        """获取调度器状态"""
        jobs = schedule.get_jobs()
        next_run = min([job.next_run for job in jobs]) if jobs else None
        
        return {
            'running': self.running,
            'total_jobs': len(jobs),
            'next_run': next_run.strftime('%Y-%m-%d %H:%M:%S') if next_run else None,
            'recent_jobs': len(self.job_history)
        }

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强版定时任务调度器')
    parser.add_argument('--action', 
                       choices=['start', 'stop', 'status', 'history', 'test'], 
                       default='start',
                       help='操作类型')
    parser.add_argument('--days', 
                       type=int, 
                       default=7,
                       help='查看历史的天数')
    
    args = parser.parse_args()
    
    scheduler = EnhancedScheduler()
    
    if args.action == 'start':
        try:
            scheduler.start()
        except KeyboardInterrupt:
            logger.info("接收到停止信号，正在关闭调度器...")
            scheduler.stop()
    elif args.action == 'status':
        status = scheduler.get_status()
        logger.info("调度器状态:")
        logger.info(f"  运行状态: {'运行中' if status['running'] else '已停止'}")
        logger.info(f"  任务数量: {status['total_jobs']}")
        logger.info(f"  下次运行: {status['next_run'] or '无'}")
        logger.info(f"  历史任务: {status['recent_jobs']} 条")
    elif args.action == 'history':
        history = scheduler.get_job_history(args.days)
        logger.info(f"最近 {args.days} 天的任务历史:")
        for job in history:
            status = "成功" if job['success'] else "失败"
            duration = job.get('duration', 0)
            logger.info(f"  {job['name']}: {status} (耗时: {duration:.2f}s)")
    elif args.action == 'test':
        logger.info("执行测试任务...")
        scheduler.run_morning_sync()
        scheduler.run_statistics_report()

if __name__ == '__main__':
    main()
