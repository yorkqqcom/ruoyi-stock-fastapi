#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日资金流数据同步脚本
专门用于同步当日的资金流向数据
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, date
from loguru import logger
import argparse

from dao.database import db_manager
from services.moneyflow_service import MoneyFlowService

def sync_daily_moneyflow():
    """同步当日资金流数据"""
    try:
        logger.info("开始同步当日资金流数据")
        
        # 创建服务实例
        service = MoneyFlowService()
        
        # 获取数据库会话
        session = db_manager.get_session()
        
        try:
            # 同步资金流向数据
            count = service.sync_daily_data_optimized(session)
            logger.info(f"资金流数据同步完成，共处理 {count} 条记录")
            return count
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"资金流数据同步失败: {e}")
        raise

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='每日资金流数据同步脚本')
    parser.add_argument('--verbose', '-v', 
                       action='store_true',
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logger.remove()
        logger.add(sys.stdout, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    
    try:
        count = sync_daily_moneyflow()
        
        if count > 0:
            logger.info("资金流数据同步成功完成")
            sys.exit(0)
        else:
            logger.warning("没有新的资金流数据需要同步")
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在退出...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
