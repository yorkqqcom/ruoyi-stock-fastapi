"""
配置文件
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv('1-init/stock.env')

class Config:
    """应用配置类"""
    
    # Tushare配置
    TUSHARE_TOKEN = os.getenv('TUSHARE_TOKEN', '')
    
    # 数据库配置
    DB_DRIVER = os.getenv('DB_DRIVER', 'mysql+pymysql')
    DB_USER = os.getenv('DB_USER', 'tushare')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'tushare')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'tushare')
    DB_CHARSET = os.getenv('DB_CHARSET', 'utf8')
    
    # 数据库连接URL
    DATABASE_URL = f"{DB_DRIVER}://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={DB_CHARSET}"
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/tushare_data.log')
    
    # 数据更新配置
    BATCH_SIZE = int(os.getenv('BATCH_SIZE', '1000'))  # 批处理大小
    MAX_RETRY = int(os.getenv('MAX_RETRY', '3'))  # 最大重试次数
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '60'))  # 重试延迟(秒)

# 创建配置实例
config = Config()
