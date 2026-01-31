import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from datetime import datetime

from config.database import AsyncSessionLocal
from config.env import DataBaseConfig
from module_factor.dao.factor_dao import FactorCalcLogDao, FactorDefinitionDao, FactorTaskDao
from module_factor.entity.do.factor_do import FactorCalcLog
from module_factor.entity.vo.factor_vo import FactorTaskModel
from module_factor.service.factor_calc_service import FactorCalcService
from utils.log_util import logger


async def run_factor_task(task_id: int, session: AsyncSession | None = None) -> None:
    """
    因子计算异步入口
    """
    start_time = datetime.now()
    use_external_session = session is not None
    task: Any | None = None
    task_name = ''
    task_factor_codes = ''
    task_symbol_universe = ''
    task_start_date = ''
    task_end_date = ''
    error_message = ''

    try:
        if session is None:
            session_context = AsyncSessionLocal()
            session = await session_context.__aenter__()
        else:
            session_context = None

        # 1. 加载任务配置
        task_do = await FactorTaskDao.get_task_by_id(session, task_id)
        if not task_do:
            logger.error(f'因子任务ID {task_id} 不存在')
            error_message = f'因子任务ID {task_id} 不存在'
            task_name = f'task_{task_id}'
            raise ValueError(error_message)

        # 这里直接使用 ORM 对象 task_do，避免 Pydantic 模型映射问题
        task = task_do

        # 提前缓存任务关键字段
        task_name = getattr(task, 'task_name', None) or (f'task_{task_id}' if task_id else 'task_unknown')
        task_factor_codes = getattr(task, 'factor_codes', '') or ''
        task_symbol_universe = getattr(task, 'symbol_universe', '') or ''
        task_start_date = getattr(task, 'start_date', '') or ''
        task_end_date = getattr(task, 'end_date', '') or ''

        # 调试日志：查看任务在代码中的实际字段值
        logger.warning(
            f'DEBUG_TASK id={task.id}, task_name={task_name!r}, '
            f'factor_codes_raw={task_factor_codes!r}'
        )

        # 2. 加载因子定义
        factor_codes: list[str] = []
        raw_codes = getattr(task, 'factor_codes', None)
        if raw_codes:
            factor_codes = [code.strip() for code in raw_codes.split(',') if code.strip()]

        factor_defs: list[Any] = []
        for code in factor_codes:
            definition = await FactorDefinitionDao.get_definition_by_code(session, code)
            if definition:
                factor_defs.append(definition)

        # 调试日志：查看解析出的因子代码以及查到的因子定义
        logger.warning(
            f'DEBUG_DEFS input_codes={factor_codes!r}, '
            f'found_defs={[d.factor_code for d in factor_defs]!r}'
        )

        if not factor_defs:
            error_message = f'因子任务 {task_name} (ID: {task.id}) 未找到任何有效因子定义'
            logger.warning(error_message)
            raise ValueError(error_message)

        # 调用真正的因子计算引擎（内部会提交事务）
        await FactorCalcService.calc_task(session, task_do, factor_defs)
        
        # 更新任务统计信息（成功）
        # 注意：calc_task内部已经提交了事务，这里需要重新开始一个事务
        try:
            await FactorTaskDao.update_task_run_stats_dao(
                session, task_id, is_success=True, last_run_time=datetime.now()
            )
            await session.commit()
        except Exception as stats_exc:  # noqa: BLE001
            logger.exception('更新任务统计信息失败: %s', stats_exc)
            await session.rollback()
    except Exception as exc:  # noqa: BLE001
        # 记录错误日志
        duration = int((datetime.now() - start_time).total_seconds())
        error_msg = str(exc)[:2000]  # 限制错误信息长度
        logger.exception('因子任务执行失败: %s', exc)
        
        try:
            log = FactorCalcLog(
                task_id=task_id or 0,
                task_name=task_name or f'task_{task_id}',
                factor_codes=task_factor_codes,
                symbol_universe=task_symbol_universe,
                start_date=task_start_date,
                end_date=task_end_date,
                status='1',
                record_count=0,
                duration=duration,
                error_message=error_msg,
                create_time=datetime.now(),
            )
            if session:
                await FactorCalcLogDao.add_log_dao(session, log)
                await session.commit()
        except Exception as log_exc:  # noqa: BLE001
            logger.exception('写入因子计算错误日志失败: %s', log_exc)
        
        # 更新任务统计信息（失败）
        try:
            if session:
                await FactorTaskDao.update_task_run_stats_dao(
                    session, task_id, is_success=False, last_run_time=datetime.now()
                )
                await session.commit()
        except Exception as stats_exc:  # noqa: BLE001
            logger.exception('更新任务统计信息失败: %s', stats_exc)
    finally:
        if not use_external_session and session is not None:
            await session.close()


def run_factor_task_sync(task_id: int) -> None:
    """
    同步入口，供调度器调用（与 Tushare 下载任务类似，独立事件循环和连接池）
    """
    from urllib.parse import quote_plus

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        async_db_url = (
            f'mysql+asyncmy://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
            f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
        )
        if DataBaseConfig.db_type == 'postgresql':
            async_db_url = (
                f'postgresql+asyncpg://{DataBaseConfig.db_username}:{quote_plus(DataBaseConfig.db_password)}@'
                f'{DataBaseConfig.db_host}:{DataBaseConfig.db_port}/{DataBaseConfig.db_database}'
            )

        thread_engine = create_async_engine(
            async_db_url,
            echo=DataBaseConfig.db_echo,
            max_overflow=DataBaseConfig.db_max_overflow,
            pool_size=DataBaseConfig.db_pool_size,
            pool_recycle=DataBaseConfig.db_pool_recycle,
            pool_timeout=DataBaseConfig.db_pool_timeout,
        )
        ThreadSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=thread_engine)

        async def run_with_session() -> None:
            async with ThreadSessionLocal() as session:
                await run_factor_task(task_id, session=session)

        loop.run_until_complete(run_with_session())
        loop.run_until_complete(thread_engine.dispose())
    finally:
        loop.close()

