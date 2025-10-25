"""
股票基础信息同步脚本
专门用于股票基础信息的日常更新（上市、退市、暂停等状态变更）
注意：此脚本仅处理股票基础信息，不包含行情数据同步
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dao.database import db_manager
from services.stock_basic_service import StockBasicService
from loguru import logger
import argparse
from datetime import datetime

def daily_sync_stock_basic():
    """日常同步股票基础信息数据"""
    try:
        logger.info("开始日常同步股票基础信息数据")
        
        # 创建服务实例
        service = StockBasicService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 更新股票状态（包括新增上市、退市、暂停上市等）
            count = service.update_stock_status(session)
            logger.info(f"日常同步股票基础信息完成，共处理 {count} 条记录")
            
            # 获取统计信息
            stats = service.get_stock_statistics(session)
            logger.info(f"当前股票统计信息: {stats}")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"日常同步股票基础信息失败: {e}")
        raise

def sync_active_stocks():
    """同步正常上市股票信息"""
    try:
        logger.info("开始同步正常上市股票信息")
        
        # 创建服务实例
        service = StockBasicService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 同步正常上市股票
            count = service.sync_all_stock_basic(session)
            logger.info(f"同步正常上市股票完成，共处理 {count} 条记录")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"同步正常上市股票失败: {e}")
        raise

def sync_delisted_stocks():
    """同步已退市股票信息"""
    try:
        logger.info("开始同步已退市股票信息")
        
        # 创建服务实例
        service = StockBasicService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 同步已退市股票
            count = service.sync_delisted_stocks(session)
            logger.info(f"同步已退市股票完成，共处理 {count} 条记录")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"同步已退市股票失败: {e}")
        raise

def sync_suspended_stocks():
    """同步暂停上市股票信息"""
    try:
        logger.info("开始同步暂停上市股票信息")
        
        # 创建服务实例
        service = StockBasicService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 同步暂停上市股票
            count = service.sync_suspended_stocks(session)
            logger.info(f"同步暂停上市股票完成，共处理 {count} 条记录")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"同步暂停上市股票失败: {e}")
        raise

def get_stock_statistics():
    """获取股票统计信息"""
    try:
        logger.info("开始获取股票统计信息")
        
        # 创建服务实例
        service = StockBasicService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 获取统计信息
            stats = service.get_stock_statistics(session)
            logger.info(f"股票统计信息: {stats}")
            return stats
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"获取股票统计信息失败: {e}")
        raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='日常数据同步脚本')
    parser.add_argument('--action', 
                       choices=['daily', 'active', 'delisted', 'suspended', 'stats'], 
                       default='daily',
                       help='同步类型')
    
    args = parser.parse_args()
    
    if args.action == 'daily':
        daily_sync_stock_basic()
    elif args.action == 'active':
        sync_active_stocks()
    elif args.action == 'delisted':
        sync_delisted_stocks()
    elif args.action == 'suspended':
        sync_suspended_stocks()
    elif args.action == 'stats':
        get_stock_statistics()

if __name__ == '__main__':
    main()
