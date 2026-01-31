import asyncio
import threading
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config.env import DataBaseConfig
from module_factor.entity.vo.factor_vo import ModelTrainRequestModel
from module_factor.service.model_train_service import ModelTrainService
from utils.log_util import logger


def run_model_train_task_sync(
    db_session_factory: Any, task_id: int, request: ModelTrainRequestModel
) -> None:
    """
    同步执行模型训练任务（在线程中运行）
    在新线程中创建新的事件循环和数据库连接，避免事件循环冲突

    :param db_session_factory: 数据库会话工厂（保留参数以兼容调用，但实际不使用）
    :param task_id: 任务ID
    :param request: 训练请求
    """
    # 在新线程中创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 在新线程中创建新的数据库引擎和会话
        # 这样可以避免事件循环冲突
        async_db_url = (
            f'mysql+asyncmy://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
            f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
        )
        if DataBaseConfig.db_type == 'postgresql':
            async_db_url = (
                f'postgresql+asyncpg://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
                f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
            )
        
        # 创建新的引擎，绑定到当前线程的事件循环
        thread_engine = create_async_engine(
            async_db_url,
            echo=DataBaseConfig.db_echo,
            max_overflow=DataBaseConfig.db_max_overflow,
            pool_size=DataBaseConfig.db_pool_size,
            pool_recycle=DataBaseConfig.db_pool_recycle,
            pool_timeout=DataBaseConfig.db_pool_timeout,
        )
        ThreadSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=thread_engine)
        
        # 使用新会话运行训练任务
        async def run_async():
            async with ThreadSessionLocal() as db:
                try:
                    logger.info(f'开始执行模型训练任务，任务ID：{task_id}')
                    result = await ModelTrainService.train_model_service(db, request, task_id)
                    if result.is_success:
                        logger.info(f'模型训练任务执行成功，任务ID：{task_id}')
                    else:
                        logger.error(f'模型训练任务执行失败，任务ID：{task_id}，错误：{result.message}')
                except Exception as e:
                    logger.error(f'模型训练任务执行异常，任务ID：{task_id}，错误：{str(e)}', exc_info=True)
        
        # 运行异步函数
        loop.run_until_complete(run_async())
        
        # 清理引擎
        loop.run_until_complete(thread_engine.dispose())
    finally:
        # 清理事件循环
        loop.close()
        asyncio.set_event_loop(None)


def execute_model_train_task(db_session_factory: Any, task_id: int, request: ModelTrainRequestModel) -> None:
    """
    在后台线程中执行模型训练任务

    :param db_session_factory: 数据库会话工厂
    :param task_id: 任务ID
    :param request: 训练请求
    """
    thread = threading.Thread(
        target=run_model_train_task_sync,
        args=(db_session_factory, task_id, request),
        daemon=True,
        name=f'ModelTrainTask-{task_id}',
    )
    thread.start()
    logger.info(f'模型训练任务已在后台线程启动，任务ID：{task_id}')
