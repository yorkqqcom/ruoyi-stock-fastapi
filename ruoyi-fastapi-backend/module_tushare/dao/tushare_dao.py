from collections.abc import Sequence
from typing import Any
from datetime import datetime

import pandas as pd
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_tushare.entity.do.tushare_do import (
    TushareApiConfig,
    TushareData,
    TushareDownloadLog,
    TushareDownloadRun,
    TushareDownloadTask,
    TushareWorkflowConfig,
    TushareWorkflowStep,
)
from module_tushare.entity.vo.tushare_vo import (
    TushareApiConfigModel,
    TushareApiConfigPageQueryModel,
    TushareDataModel,
    TushareDataPageQueryModel,
    TushareDownloadLogPageQueryModel,
    TushareDownloadTaskModel,
    TushareDownloadTaskPageQueryModel,
    TushareWorkflowConfigModel,
    TushareWorkflowConfigPageQueryModel,
    TushareWorkflowStepModel,
    TushareWorkflowStepPageQueryModel,
)
from utils.common_util import CamelCaseUtil
from utils.page_util import PageUtil


class TushareApiConfigDao:
    """
    Tushare接口配置管理模块数据库操作层
    """

    @classmethod
    async def get_config_detail_by_id(cls, db: AsyncSession, config_id: int) -> TushareApiConfig | None:
        """
        根据配置id获取配置详细信息

        :param db: orm对象
        :param config_id: 配置id
        :return: 配置信息对象
        """
        config_info = (await db.execute(select(TushareApiConfig).where(TushareApiConfig.config_id == config_id))).scalars().first()

        return config_info

    @classmethod
    async def get_config_detail_by_info(
        cls, db: AsyncSession, config: TushareApiConfigModel
    ) -> TushareApiConfig | None:
        """
        根据配置参数获取配置信息

        :param db: orm对象
        :param config: 配置参数对象
        :return: 配置信息对象
        """
        config_info = (
            (
                await db.execute(
                    select(TushareApiConfig).where(
                        TushareApiConfig.api_code == config.api_code,
                    )
                )
            )
            .scalars()
            .first()
        )

        return config_info

    @classmethod
    async def get_config_list(
        cls, db: AsyncSession, query_object: TushareApiConfigPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取配置列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 配置列表信息对象
        """
        query = (
            select(TushareApiConfig)
            .where(
                TushareApiConfig.api_name.like(f'%{query_object.api_name}%') if query_object.api_name else True,
                TushareApiConfig.api_code.like(f'%{query_object.api_code}%') if query_object.api_code else True,
                TushareApiConfig.status == query_object.status if query_object.status else True,
            )
            .order_by(TushareApiConfig.config_id)
            .distinct()
        )

        config_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return config_list

    @classmethod
    async def add_config_dao(cls, db: AsyncSession, config: TushareApiConfigModel) -> TushareApiConfig:
        """
        新增配置信息

        :param db: orm对象
        :param config: 配置对象
        :return: 配置对象
        """
        db_config = TushareApiConfig(**config.model_dump(exclude={'config_id'}))
        db.add(db_config)
        await db.flush()
        await db.refresh(db_config)
        return db_config

    @classmethod
    async def edit_config_dao(
        cls, db: AsyncSession, config_id_or_model: int | TushareApiConfigModel, config_dict: dict[str, Any] | None = None
    ) -> int:
        """
        编辑配置信息

        :param db: orm对象
        :param config_id_or_model: 配置ID（int）或配置模型对象（TushareApiConfigModel）
        :param config_dict: 配置字段字典（snake_case格式），当第一个参数是config_id时使用
        :return: 编辑结果
        """
        # 支持两种调用方式：1) edit_config_dao(db, config_id, config_dict) 2) edit_config_dao(db, config_model)
        if isinstance(config_id_or_model, TushareApiConfigModel):
            # 旧的方式：传入模型对象
            config = config_id_or_model
            config_id = config.config_id
            if config_id is None:
                raise ValueError('config_id不能为None')
            # 使用 by_alias=False 获取 snake_case 格式的字段名，以便与数据库字段匹配
            # 使用 exclude_none=False 确保即使值为 None 的字段（如 primary_key_fields）也能被正确更新
            config_dict = config.model_dump(exclude={'config_id'}, exclude_none=False, by_alias=False)
        else:
            # 新的方式：直接传入config_id和字典
            config_id = config_id_or_model
            if config_dict is None:
                raise ValueError('当使用config_id时，必须提供config_dict参数')
        
        # 从字典中移除 config_id，因为它只用于 WHERE 条件
        update_dict = {k: v for k, v in config_dict.items() if k != 'config_id'}
        
        await db.execute(
            update(TushareApiConfig)
            .where(TushareApiConfig.config_id == config_id)
            .values(**update_dict)
        )
        return config_id

    @classmethod
    async def delete_config_dao(cls, db: AsyncSession, config_ids: Sequence[int]) -> int:
        """
        删除配置信息

        :param db: orm对象
        :param config_ids: 配置id列表
        :return: 删除结果
        """
        result = await db.execute(delete(TushareApiConfig).where(TushareApiConfig.config_id.in_(config_ids)))
        return result.rowcount


class TushareDownloadTaskDao:
    """
    Tushare下载任务管理模块数据库操作层
    """

    @classmethod
    async def get_task_detail_by_id(cls, db: AsyncSession, task_id: int) -> TushareDownloadTask | None:
        """
        根据任务id获取任务详细信息

        :param db: orm对象
        :param task_id: 任务id
        :return: 任务信息对象
        """
        task_info = (
            (await db.execute(select(TushareDownloadTask).where(TushareDownloadTask.task_id == task_id)))
            .scalars()
            .first()
        )

        return task_info

    @classmethod
    async def get_task_detail_by_info(
        cls, db: AsyncSession, task: TushareDownloadTaskModel
    ) -> TushareDownloadTask | None:
        """
        根据任务参数获取任务信息

        :param db: orm对象
        :param task: 任务参数对象
        :return: 任务信息对象
        """
        task_info = (
            (
                await db.execute(
                    select(TushareDownloadTask).where(
                        TushareDownloadTask.task_name == task.task_name,
                    )
                )
            )
            .scalars()
            .first()
        )

        return task_info

    @classmethod
    async def get_task_list(
        cls, db: AsyncSession, query_object: TushareDownloadTaskPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取任务列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 任务列表信息对象
        """
        # 构建查询条件列表
        conditions = []
        
        # 任务名称模糊查询
        if query_object.task_name:
            conditions.append(TushareDownloadTask.task_name.like(f'%{query_object.task_name}%'))
        
        # 接口配置ID精确查询
        if query_object.config_id is not None:
            conditions.append(TushareDownloadTask.config_id == query_object.config_id)
        
        # 流程配置ID精确查询
        if query_object.workflow_id is not None:
            conditions.append(TushareDownloadTask.workflow_id == query_object.workflow_id)
        
        # 状态精确查询
        if query_object.status is not None:
            conditions.append(TushareDownloadTask.status == query_object.status)
        
        # 根据任务类型筛选（task_type: single -> workflow_id is None, workflow -> workflow_id is not None）
        from utils.log_util import logger
        task_type_value = getattr(query_object, 'task_type', None) if hasattr(query_object, 'task_type') else None
        logger.info(f'[DAO查询任务列表] task_type参数值: {task_type_value}, 类型: {type(task_type_value)}')
        
        # 只有当 task_type 有明确的值（不是 None、空字符串或空值）时才添加过滤条件
        if task_type_value and task_type_value.strip() if isinstance(task_type_value, str) else task_type_value:
            if task_type_value == 'single':
                conditions.append(TushareDownloadTask.workflow_id.is_(None))
                logger.info(f'[DAO查询任务列表] 添加条件: workflow_id IS NULL (single类型)')
            elif task_type_value == 'workflow':
                conditions.append(TushareDownloadTask.workflow_id.isnot(None))
                logger.info(f'[DAO查询任务列表] 添加条件: workflow_id IS NOT NULL (workflow类型)')
        else:
            logger.info(f'[DAO查询任务列表] 未指定task_type或task_type为空，返回所有类型的任务')
        
        # 构建查询
        query = select(TushareDownloadTask)
        if conditions:
            query = query.where(*conditions)
        query = query.order_by(TushareDownloadTask.task_id).distinct()
        
        logger.info(f'[DAO查询任务列表] 查询条件数量: {len(conditions)}')
        logger.info(f'[DAO查询任务列表] 分页参数: page_num={query_object.page_num}, page_size={query_object.page_size}, is_page={is_page}')

        config_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        
        logger.info(f'[DAO查询任务列表] 查询结果类型: {type(config_list)}')
        if isinstance(config_list, dict) and 'rows' in config_list:
            logger.info(f'[DAO查询任务列表] 分页结果: total={config_list.get("total")}, rows数量={len(config_list.get("rows", []))}')
        elif isinstance(config_list, list):
            logger.info(f'[DAO查询任务列表] 列表结果数量: {len(config_list)}')
        
        return config_list

    @classmethod
    async def add_task_dao(cls, db: AsyncSession, task: TushareDownloadTaskModel) -> TushareDownloadTask:
        """
        新增任务信息

        :param db: orm对象
        :param task: 任务对象
        :return: 任务对象
        """
        # 使用 by_alias=False 确保使用 snake_case 字段名，与数据库字段匹配
        # 使用 exclude_none=False 确保所有字段（包括None值）都被包含，避免字段丢失
        task_dict = task.model_dump(exclude={'task_id'}, by_alias=False, exclude_none=False)
        from utils.log_util import logger
        logger.info(f'[DAO新增任务] 准备插入的字典: {task_dict}')
        logger.info(f'[DAO新增任务] task_name值: {task_dict.get("task_name")}')
        
        # 确保 task_name 不为空
        if not task_dict.get('task_name') or (isinstance(task_dict.get('task_name'), str) and not task_dict.get('task_name').strip()):
            logger.error(f'[DAO新增任务] task_name为空或无效: {task_dict.get("task_name")}')
            raise ValueError('任务名称不能为空')
        
        db_task = TushareDownloadTask(**task_dict)
        db.add(db_task)
        await db.flush()
        await db.refresh(db_task)
        return db_task

    @classmethod
    async def edit_task_dao(
        cls, db: AsyncSession, task_id_or_model: int | TushareDownloadTaskModel, task_dict: dict[str, Any] | None = None
    ) -> int:
        """
        编辑任务信息

        :param db: orm对象
        :param task_id_or_model: 任务ID（int）或任务模型对象（TushareDownloadTaskModel）
        :param task_dict: 任务字段字典（snake_case格式），当第一个参数是task_id时使用
        :return: 编辑结果
        """
        from utils.log_util import logger
        
        # 支持两种调用方式：1) edit_task_dao(db, task_id, task_dict) 2) edit_task_dao(db, task_model)
        if isinstance(task_id_or_model, TushareDownloadTaskModel):
            # 旧的方式：传入模型对象
            task = task_id_or_model
            task_id = task.task_id
            if task_id is None:
                raise ValueError('task_id不能为None')
            task_dict = task.model_dump(
                exclude={
                    'task_id',
                    'last_run_time', 'next_run_time', 'run_count', 'success_count', 'fail_count',
                    'create_by', 'create_time'
                },
                exclude_none=False,
                by_alias=False
            )
        else:
            # 新的方式：直接传入task_id和字典
            task_id = task_id_or_model
            if task_dict is None:
                raise ValueError('当使用task_id时，必须提供task_dict参数')
        
        logger.info(f'[DAO编辑任务] 开始更新，task_id: {task_id}')
        logger.info(f'[DAO编辑任务] 接收到的字典: {task_dict}')
        
        # 从字典中移除 task_id，因为它只用于 WHERE 条件
        update_dict = {k: v for k, v in task_dict.items() if k != 'task_id'}
        
        # 如果是通过模型对象方式调用，需要排除不应该更新的字段
        # 如果是通过字典方式调用，则信任调用者，允许更新所有字段（包括统计字段）
        if isinstance(task_id_or_model, TushareDownloadTaskModel):
            excluded_fields = {
                'last_run_time', 'next_run_time', 'run_count', 'success_count', 'fail_count',
                'create_by', 'create_time'
            }
            update_dict = {k: v for k, v in update_dict.items() if k not in excluded_fields}
        
        # 过滤掉 None 值，避免更新必填字段为 None
        update_dict = {k: v for k, v in update_dict.items() if v is not None}
        
        logger.info(f'[DAO编辑任务] 准备更新的字段字典: {update_dict}')
        logger.info(f'[DAO编辑任务] 字典键: {list(update_dict.keys())}')
        logger.info(f'[DAO编辑任务] cron_expression值: {update_dict.get("cron_expression")}, 类型: {type(update_dict.get("cron_expression"))}')
        logger.info(f'[DAO编辑任务] task_name值: {update_dict.get("task_name")}')
        
        stmt = update(TushareDownloadTask).where(TushareDownloadTask.task_id == task_id).values(**update_dict)
        logger.info(f'[DAO编辑任务] SQL语句: {stmt}')
        
        result = await db.execute(stmt)
        logger.info(f'[DAO编辑任务] 执行结果: rowcount={result.rowcount}')
        
        if result.rowcount == 0:
            logger.warning(f'[DAO编辑任务] 警告：没有更新任何记录，task_id: {task_id}')
        
        return task_id

    @classmethod
    async def delete_task_dao(cls, db: AsyncSession, task_ids: Sequence[int]) -> int:
        """
        删除任务信息

        :param db: orm对象
        :param task_ids: 任务id列表
        :return: 删除结果
        """
        result = await db.execute(delete(TushareDownloadTask).where(TushareDownloadTask.task_id.in_(task_ids)))
        return result.rowcount

    @classmethod
    async def get_tasks_for_scheduler(cls, db: AsyncSession) -> list[TushareDownloadTask]:
        """
        查询所有需要注册到调度器的任务（状态为启用且有cron表达式）

        :param db: orm对象
        :return: 任务列表
        """
        tasks = (
            await db.execute(
                select(TushareDownloadTask)
                .where(
                    TushareDownloadTask.status == '0',  # 状态为启用
                    TushareDownloadTask.cron_expression.isnot(None),  # cron表达式不为空
                    TushareDownloadTask.cron_expression != '',  # cron表达式不为空字符串
                )
                .order_by(TushareDownloadTask.task_id)
            )
        ).scalars().all()

        return list(tasks)


class TushareDownloadLogDao:
    """
    Tushare下载日志管理模块数据库操作层
    """

    @classmethod
    async def get_log_list(
        cls, db: AsyncSession, query_object: TushareDownloadLogPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取日志列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 日志列表信息对象
        """
        from module_tushare.entity.do.tushare_do import TushareDownloadTask
        
        # 根据任务类型筛选（通过关联任务表判断）
        task_type_filter = True
        if hasattr(query_object, 'task_type') and query_object.task_type:
            if query_object.task_type == 'single':
                # 单个接口任务：task_name 不包含 [，且关联的任务 workflow_id 为 None
                task_type_filter = ~TushareDownloadLog.task_name.like('%[%')
            elif query_object.task_type == 'workflow':
                # 流程配置任务：task_name 包含 [
                task_type_filter = TushareDownloadLog.task_name.like('%[%')
        
        query = (
            select(TushareDownloadLog)
            .where(
                TushareDownloadLog.task_id == query_object.task_id if query_object.task_id else True,
                TushareDownloadLog.task_name.like(f'%{query_object.task_name}%') if query_object.task_name else True,
                TushareDownloadLog.status == query_object.status if query_object.status else True,
                task_type_filter,
            )
            .order_by(TushareDownloadLog.log_id.desc())
            .distinct()
        )

        config_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return config_list

    @classmethod
    async def add_log_dao(cls, db: AsyncSession, log: TushareDownloadLog) -> TushareDownloadLog:
        """
        新增日志信息

        :param db: orm对象
        :param log: 日志对象
        :return: 日志对象
        """
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    @classmethod
    async def delete_log_dao(cls, db: AsyncSession, log_ids: Sequence[int]) -> int:
        """
        删除日志信息

        :param db: orm对象
        :param log_ids: 日志id列表
        :return: 删除结果
        """
        result = await db.execute(delete(TushareDownloadLog).where(TushareDownloadLog.log_id.in_(log_ids)))
        return result.rowcount

    @classmethod
    async def clear_log_dao(cls, db: AsyncSession) -> int:
        """
        清空所有日志信息

        :param db: orm对象
        :return: 删除结果
        """
        result = await db.execute(delete(TushareDownloadLog))
        return result.rowcount


class TushareDownloadRunDao:
    """
    Tushare下载任务运行表（运行总览）数据库操作层
    """

    @classmethod
    async def create_run_record(
        cls,
        db: AsyncSession,
        task: TushareDownloadTask,
        initial_status: str = 'PENDING',
    ) -> TushareDownloadRun:
        """
        创建一条运行记录（初始为 PENDING 或 RUNNING）
        """
        run = TushareDownloadRun(
            task_id=task.task_id,
            task_name=task.task_name,
            status=initial_status,
            start_time=None,
            end_time=None,
            progress=0,
            total_records=0,
            success_records=0,
            fail_records=0,
        )
        db.add(run)
        await db.flush()
        await db.refresh(run)
        return run

    @classmethod
    async def update_run_status(
        cls,
        db: AsyncSession,
        run_id: int,
        status: str | None = None,
        progress: int | None = None,
        total_records: int | None = None,
        success_records: int | None = None,
        fail_records: int | None = None,
        error_message: str | None = None,
        set_start_time: bool = False,
        set_end_time: bool = False,
    ) -> int:
        """
        更新运行记录的状态/进度/统计信息
        """
        values: dict[str, Any] = {}
        if status is not None:
            values['status'] = status
        if progress is not None:
            values['progress'] = progress
        if total_records is not None:
            values['total_records'] = total_records
        if success_records is not None:
            values['success_records'] = success_records
        if fail_records is not None:
            values['fail_records'] = fail_records
        if error_message is not None:
            values['error_message'] = error_message
        now = datetime.now()
        if set_start_time:
            values['start_time'] = now
        if set_end_time:
            values['end_time'] = now
        if values:
            values['update_time'] = now
            await db.execute(
                update(TushareDownloadRun).where(TushareDownloadRun.run_id == run_id).values(**values)
            )
        return run_id


class TushareDataDao:
    """
    Tushare数据存储管理模块数据库操作层
    """

    @classmethod
    async def get_data_list(
        cls, db: AsyncSession, query_object: TushareDataPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        获取数据列表

        :param db: orm对象
        :param query_object: 查询对象
        :param is_page: 是否分页
        :return: 数据列表
        """
        query = (
            select(TushareData)
            .where(
                TushareData.task_id == query_object.task_id if query_object.task_id else True,
                TushareData.config_id == query_object.config_id if query_object.config_id else True,
                TushareData.api_code.like(f'%{query_object.api_code}%') if query_object.api_code else True,
                TushareData.download_date == query_object.download_date if query_object.download_date else True,
            )
            .order_by(TushareData.data_id.desc())
            .distinct()
        )
        data_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )

        return data_list

    @classmethod
    async def add_data_dao(cls, db: AsyncSession, data: TushareData) -> TushareData:
        """
        新增数据

        :param db: orm对象
        :param data: 数据对象
        :return: 新增的数据对象
        """
        db.add(data)
        await db.flush()
        return data

    @classmethod
    async def add_data_batch_dao(cls, db: AsyncSession, data_list: list[TushareData]) -> list[TushareData]:
        """
        批量新增数据

        :param db: orm对象
        :param data_list: 数据对象列表
        :return: 新增的数据对象列表
        """
        db.add_all(data_list)
        await db.flush()
        return data_list

    @classmethod
    async def detect_unique_keys(cls, db: AsyncSession, table_name: str) -> list[str]:
        """
        自动检测表的唯一键字段（主键或唯一索引）
        
        :param db: 数据库会话
        :param table_name: 表名
        :return: 唯一键字段列表
        """
        from sqlalchemy import text
        from config.env import DataBaseConfig
        import re
        
        # 验证表名，防止SQL注入
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f'无效的表名: {table_name}')
        
        unique_keys = []
        
        if DataBaseConfig.db_type == 'postgresql':
            # PostgreSQL: 查询主键和唯一索引
            query_sql = """
                SELECT DISTINCT ccu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                    ON tc.constraint_name = ccu.constraint_name
                    AND tc.table_schema = ccu.table_schema
                WHERE tc.table_schema = 'public'
                    AND tc.table_name = :table_name
                    AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                ORDER BY ccu.column_name
            """
            result = await db.execute(text(query_sql), {'table_name': table_name})
            unique_keys = [row[0] for row in result.fetchall()]
        else:
            # MySQL: 查询主键和唯一索引
            query_sql = """
                SELECT DISTINCT kcu.column_name
                FROM information_schema.key_column_usage kcu
                JOIN information_schema.table_constraints tc
                    ON kcu.constraint_name = tc.constraint_name
                    AND kcu.table_schema = tc.table_schema
                    AND kcu.table_name = tc.table_name
                WHERE kcu.table_schema = DATABASE()
                    AND kcu.table_name = :table_name
                    AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
                ORDER BY kcu.ordinal_position, kcu.column_name
            """
            result = await db.execute(text(query_sql), {'table_name': table_name})
            unique_keys = [row[0] for row in result.fetchall()]
        
        return unique_keys

    @classmethod
    async def get_unique_key_fields(
        cls, db: AsyncSession, table_name: str, config=None, step_unique_key_fields: list[str] | None = None, primary_key_fields_str: str | None = None
    ) -> list[str]:
        """
        获取唯一键字段，按照优先级：
        1. 步骤配置的 unique_key_fields（节点级别）
        2. 如果表已存在，且接口配置的主键字段也有，则优先使用接口配置的主键字段
        3. 如果表已存在，使用表实际主键
        4. 接口配置的 primary_key_fields（接口级别，如果表不存在）
        5. 自动检测表的唯一键（如果表存在）
        
        :param db: 数据库会话
        :param table_name: 表名
        :param config: 接口配置对象（可选，用于向后兼容，但优先使用 primary_key_fields_str）
        :param step_unique_key_fields: 步骤配置的唯一键字段（可选）
        :param primary_key_fields_str: 主键字段JSON字符串（可选，优先使用此参数避免访问 config 对象）
        :return: 唯一键字段列表
        """
        from sqlalchemy import text
        from config.env import DataBaseConfig
        from utils.log_util import logger
        
        # 第一优先级：步骤配置的唯一键字段
        if step_unique_key_fields and len(step_unique_key_fields) > 0:
            logger.debug(f'使用步骤配置的唯一键字段: {step_unique_key_fields}')
            return step_unique_key_fields
        
        # 检查表是否存在
        table_exists = False
        if DataBaseConfig.db_type == 'postgresql':
            check_sql = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = :table_name
                )
            """
        else:
            check_sql = """
                SELECT COUNT(*) as count
                FROM information_schema.tables 
                WHERE table_schema = DATABASE()
                AND table_name = :table_name
            """
        
        result = await db.execute(text(check_sql), {'table_name': table_name})
        if DataBaseConfig.db_type == 'postgresql':
            table_exists = result.scalar()
        else:
            table_exists = result.scalar() > 0
        
        # 第二优先级：如果表已存在，且接口配置的主键字段也有，则优先使用接口配置的主键字段
        # 优先使用传入的 primary_key_fields_str，避免访问 config 对象导致延迟加载
        if table_exists and primary_key_fields_str:
            try:
                import json
                config_pk_fields = json.loads(primary_key_fields_str)
                if isinstance(config_pk_fields, list) and len(config_pk_fields) > 0:
                    logger.debug(f'表 {table_name} 已存在，且接口配置的主键字段也有，优先使用接口配置的主键字段: {config_pk_fields}')
                    return config_pk_fields
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析主键字段字符串失败: {e}')
        
        # 如果 primary_key_fields_str 为空，尝试从 config 对象获取（向后兼容，但可能触发延迟加载）
        if table_exists and config and hasattr(config, 'primary_key_fields') and config.primary_key_fields:
            try:
                import json
                config_pk_fields = json.loads(config.primary_key_fields)
                if isinstance(config_pk_fields, list) and len(config_pk_fields) > 0:
                    logger.debug(f'表 {table_name} 已存在，且接口配置的主键字段也有，优先使用接口配置的主键字段: {config_pk_fields}')
                    return config_pk_fields
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析接口配置的主键字段失败: {e}')
        
        # 第三优先级：如果表已存在，使用表实际主键
        if table_exists:
            table_unique_keys = await cls.detect_unique_keys(db, table_name)
            if table_unique_keys:
                logger.debug(f'表 {table_name} 已存在，使用表实际主键: {table_unique_keys}')
                return table_unique_keys
        
        # 第四优先级：接口配置的主键字段（如果表不存在）
        # 优先使用传入的 primary_key_fields_str，避免访问 config 对象导致延迟加载
        if primary_key_fields_str:
            try:
                import json
                config_pk_fields = json.loads(primary_key_fields_str)
                if isinstance(config_pk_fields, list) and len(config_pk_fields) > 0:
                    logger.debug(f'使用接口配置的主键字段: {config_pk_fields}')
                    return config_pk_fields
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析主键字段字符串失败: {e}')
        
        # 如果 primary_key_fields_str 为空，尝试从 config 对象获取（向后兼容，但可能触发延迟加载）
        if config and hasattr(config, 'primary_key_fields') and config.primary_key_fields:
            try:
                import json
                config_pk_fields = json.loads(config.primary_key_fields)
                if isinstance(config_pk_fields, list) and len(config_pk_fields) > 0:
                    logger.debug(f'使用接口配置的主键字段: {config_pk_fields}')
                    return config_pk_fields
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f'解析接口配置的主键字段失败: {e}')
        
        # 第五优先级：自动检测表的唯一键（如果表存在）
        if table_exists:
            auto_detected = await cls.detect_unique_keys(db, table_name)
            if auto_detected:
                logger.debug(f'自动检测到表的唯一键: {auto_detected}')
                return auto_detected
        
        # 如果都没有，返回空列表
        logger.warning(f'未找到表 {table_name} 的唯一键字段')
        return []

    @classmethod
    async def _check_unique_constraint_exists(cls, db: AsyncSession, table_name: str, columns: list[str]) -> bool:
        """
        检查表是否有指定列的唯一约束
        
        :param db: 数据库会话
        :param table_name: 表名
        :param columns: 列名列表
        :return: 是否存在唯一约束
        """
        from sqlalchemy import text
        from config.env import DataBaseConfig
        from utils.log_util import logger
        
        if not columns or len(columns) == 0:
            return False
        
        try:
            if DataBaseConfig.db_type == 'postgresql':
                # PostgreSQL: 检查唯一约束或唯一索引
                # 注意：CREATE UNIQUE INDEX 创建的是索引（在 pg_index），不是约束（pg_constraint）
                # 两者都支持 ON CONFLICT，需同时检查
                columns_sorted = sorted(columns)
                columns_array_str = '{' + ','.join([f'"{col}"' for col in columns_sorted]) + '}'

                # 1) 检查 pg_constraint 中的唯一约束
                # 2) 检查 pg_index 中的唯一索引（CREATE UNIQUE INDEX 创建的不在 pg_constraint 中）
                check_sql = f"""
                    SELECT (
                        SELECT EXISTS (
                            SELECT 1
                            FROM pg_constraint c
                            JOIN pg_class t ON c.conrelid = t.oid
                            JOIN pg_namespace n ON t.relnamespace = n.oid
                            WHERE n.nspname = 'public'
                            AND t.relname = :table_name
                            AND c.contype = 'u'
                            AND array_length(c.conkey, 1) = :col_count
                            AND (
                                SELECT array_agg(a.attname::text ORDER BY a.attname)
                                FROM pg_attribute a
                                WHERE a.attrelid = c.conrelid
                                AND a.attnum = ANY(c.conkey)
                            ) = '{columns_array_str}'::text[]
                        )
                        OR EXISTS (
                            SELECT 1
                            FROM pg_index i
                            JOIN pg_class t ON i.indrelid = t.oid
                            JOIN pg_namespace n ON t.relnamespace = n.oid
                            WHERE n.nspname = 'public'
                            AND t.relname = :table_name
                            AND i.indisunique = true
                            AND (
                                SELECT array_agg(a.attname::text ORDER BY a.attname)
                                FROM pg_attribute a
                                WHERE a.attrelid = i.indrelid
                                AND a.attnum = ANY(i.indkey)
                                AND a.attnum > 0
                            ) = '{columns_array_str}'::text[]
                        )
                    )
                """

                result = await db.execute(
                    text(check_sql),
                    {
                        'table_name': table_name,
                        'col_count': len(columns)
                    }
                )
                exists = result.scalar()
                result_bool = bool(exists) if exists is not None else False
                logger.debug(f'表 {table_name} 唯一约束/索引检查: 字段 {columns} -> {result_bool}')
                return result_bool
            else:
                # MySQL: 检查唯一索引
                check_sql = """
                    SELECT COUNT(*) > 0
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                    AND table_name = :table_name
                    AND index_name IN (
                        SELECT index_name
                        FROM information_schema.statistics
                        WHERE table_schema = DATABASE()
                        AND table_name = :table_name
                        AND non_unique = 0
                        GROUP BY index_name
                        HAVING COUNT(*) = :col_count
                        AND GROUP_CONCAT(column_name ORDER BY seq_in_index) = :columns
                    )
                """
                columns_str = ','.join(columns)
                result = await db.execute(
                    text(check_sql),
                    {
                        'table_name': table_name,
                        'col_count': len(columns),
                        'columns': columns_str
                    }
                )
                return result.scalar() > 0
        except Exception as e:
            logger.warning(f'检查表 {table_name} 的唯一约束时出错: {e}，假设不存在')
            return False

    @classmethod
    async def ensure_unique_index(
        cls, db: AsyncSession, table_name: str, unique_key_fields: list[str]
    ) -> None:
        """
        确保表在指定列上存在唯一索引；若不存在则创建。
        用于 INSERT_IGNORE / UPSERT / DELETE_INSERT 等模式执行前保证唯一约束存在。

        :param db: 数据库会话
        :param table_name: 表名
        :param unique_key_fields: 唯一键列名列表
        :return: None
        """
        from sqlalchemy import text
        from config.env import DataBaseConfig
        from utils.log_util import logger
        import re

        if not unique_key_fields or len(unique_key_fields) == 0:
            return

        # 校验表名、列名（防 SQL 注入）
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            logger.warning(f'ensure_unique_index: 无效的表名 {table_name}，跳过创建唯一索引')
            return
        for col in unique_key_fields:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', col):
                logger.warning(f'ensure_unique_index: 无效的列名 {col}，跳过创建唯一索引')
                return

        try:
            # 检查表是否存在
            if DataBaseConfig.db_type == 'postgresql':
                check_sql = """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = :table_name
                    )
                """
            else:
                check_sql = """
                    SELECT COUNT(*) > 0
                    FROM information_schema.tables
                    WHERE table_schema = DATABASE()
                    AND table_name = :table_name
                """
            result = await db.execute(text(check_sql), {'table_name': table_name})
            table_exists = result.scalar() if DataBaseConfig.db_type == 'postgresql' else result.scalar() > 0
            if not table_exists:
                logger.debug(f'ensure_unique_index: 表 {table_name} 不存在，跳过创建唯一索引（由 ensure_table_exists 负责建表）')
                return

            # 检查表中是否包含 unique_key_fields 中的每一列
            if DataBaseConfig.db_type == 'postgresql':
                cols_sql = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                    AND table_name = :table_name
                """
            else:
                cols_sql = """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                    AND table_name = :table_name
                """
            result = await db.execute(text(cols_sql), {'table_name': table_name})
            existing_columns = {row[0] for row in result.fetchall()}
            missing = [c for c in unique_key_fields if c not in existing_columns]
            if missing:
                logger.warning(
                    f'ensure_unique_index: 表 {table_name} 中不存在列 {missing}，跳过创建唯一索引'
                )
                return

            # 若已存在唯一约束则直接返回
            if await cls._check_unique_constraint_exists(db, table_name, unique_key_fields):
                logger.debug(f'表 {table_name} 在字段 {unique_key_fields} 上已有唯一约束，无需创建')
                return

            # 生成索引名：uk_<table>_<col1>_<col2>_...，长度限制 PostgreSQL 63、MySQL 64
            max_len = 63 if DataBaseConfig.db_type == 'postgresql' else 64
            index_name = 'uk_' + table_name + '_' + '_'.join(unique_key_fields)
            if len(index_name) > max_len:
                index_name = index_name[:max_len]

            if DataBaseConfig.db_type == 'postgresql':
                # 使用 IF NOT EXISTS 避免索引已存在时导致事务中止（DuplicateTableError）
                table_escaped = f'"{table_name}"'
                cols_escaped = ', '.join([f'"{c}"' for c in unique_key_fields])
                create_sql = f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" ON {table_escaped} ({cols_escaped})'
            else:
                table_escaped = f'`{table_name}`'
                cols_escaped = ', '.join([f'`{c}`' for c in unique_key_fields])
                create_sql = f'CREATE UNIQUE INDEX `{index_name}` ON {table_escaped} ({cols_escaped})'

            await db.execute(text(create_sql))
            await db.flush()
            logger.info(f'已为表 {table_name} 在字段 {unique_key_fields} 上创建唯一索引: {index_name}')
        except Exception as e:
            logger.warning(f'ensure_unique_index: 为表 {table_name} 创建唯一索引失败: {e}')

    @classmethod
    async def add_dataframe_to_table_dao(
        cls, db: AsyncSession, table_name: str, df: pd.DataFrame, task_id: int, config_id: int, api_code: str, download_date: str,
        update_mode: str = '0', unique_key_fields: list[str] | None = None, config=None, primary_key_fields_str: str | None = None
    ) -> int:
        """
        将 DataFrame 批量插入到指定表（表结构与 DataFrame 列一致）
        支持多种更新模式：
        - '0': INSERT（默认，仅插入，遇到重复会报错）
        - '1': INSERT_IGNORE（忽略重复数据）
        - '2': UPSERT（存在则更新，不存在则插入）
        - '3': DELETE_INSERT（先删除再插入）

        :param db: orm对象
        :param table_name: 表名（需要验证，防止SQL注入）
        :param df: pandas DataFrame
        :param task_id: 任务ID
        :param config_id: 配置ID
        :param api_code: 接口代码
        :param download_date: 下载日期
        :param update_mode: 更新方式（'0': INSERT, '1': INSERT_IGNORE, '2': UPSERT, '3': DELETE_INSERT）
        :param unique_key_fields: 唯一键字段列表（如果为None，则自动检测）
        :param config: 接口配置对象（可选，用于向后兼容，但优先使用 primary_key_fields_str）
        :param primary_key_fields_str: 主键字段JSON字符串（可选，优先使用此参数避免访问 config 对象）
        :return: 插入的记录数
        """
        from sqlalchemy import text
        from config.env import DataBaseConfig
        from utils.log_util import logger
        import json
        import re
        from datetime import datetime

        if df is None or df.empty:
            return 0

        # 验证表名，只允许字母、数字和下划线
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f'无效的表名: {table_name}')

        # 准备列名（系统列 + DataFrame 列）
        system_columns = ['task_id', 'config_id', 'api_code', 'download_date', 'create_time']
        
        # 清理和验证 DataFrame 列名
        df_columns = []
        col_mapping = {}  # 原始列名 -> 安全列名的映射
        for col in df.columns:
            safe_col = re.sub(r'[^a-zA-Z0-9_]', '_', str(col))
            if not safe_col or safe_col[0].isdigit():
                safe_col = f'col_{safe_col}'
            df_columns.append(safe_col)
            col_mapping[col] = safe_col
        
        all_columns = system_columns + df_columns

        # 确定唯一键字段（使用新的优先级逻辑）
        # 传递提前提取的 primary_key_fields_str，避免访问 config 对象导致延迟加载
        if unique_key_fields is None or len(unique_key_fields) == 0:
            unique_key_fields = await cls.get_unique_key_fields(db, table_name, config=config, step_unique_key_fields=None, primary_key_fields_str=primary_key_fields_str)
            if unique_key_fields:
                logger.info(f'获取到表 {table_name} 的唯一键字段: {unique_key_fields}')
            else:
                logger.warning(f'表 {table_name} 未找到唯一键字段，某些更新模式可能无法正常工作')

        # 验证唯一键字段是否都存在于 all_columns 中
        if unique_key_fields:
            invalid_fields = [field for field in unique_key_fields if field not in all_columns]
            if invalid_fields:
                logger.warning(f'唯一键字段 {invalid_fields} 不在表的列中，将从唯一键字段列表中移除')
                unique_key_fields = [field for field in unique_key_fields if field in all_columns]
                if not unique_key_fields:
                    logger.warning(f'所有唯一键字段都无效，某些更新模式可能无法正常工作')

        # 如果 update_mode 是 '2' (UPSERT) 或 '3' (DELETE_INSERT)，需要唯一键
        if update_mode in ['2', '3'] and not unique_key_fields:
            logger.warning(f'更新模式 {update_mode} 需要唯一键字段，但未找到。将使用普通 INSERT 模式')
            update_mode = '0'

        # 若为需要唯一键的更新模式，确保表上存在对应唯一索引（无则创建）
        if update_mode in ('1', '2', '3') and unique_key_fields:
            await cls.ensure_unique_index(db, table_name, unique_key_fields)

        # 准备批量插入数据
        values_list = []
        create_time = datetime.now()
        
        for idx, row in df.iterrows():
            row_dict = {
                'task_id': task_id,
                'config_id': config_id,
                'api_code': api_code,
                'download_date': download_date,
                'create_time': create_time,
            }
            
            # 添加 DataFrame 的列值
            for orig_col, safe_col in zip(df.columns, df_columns):
                value = row[orig_col]
                # 处理 NaN 值
                if pd.isna(value):
                    row_dict[safe_col] = None
                else:
                    row_dict[safe_col] = value
            
            values_list.append(row_dict)

        if not values_list:
            return 0

        # 根据更新模式构建和执行 SQL
        if update_mode == '0':
            # 普通 INSERT
            if DataBaseConfig.db_type == 'postgresql':
                col_names = ', '.join([f'"{col}"' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
            else:
                col_names = ', '.join([f'`{col}`' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                insert_sql = f'INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})'
            
            result = await db.execute(text(insert_sql), values_list)
            await db.flush()
            return len(values_list)

        elif update_mode == '1':
            # INSERT_IGNORE
            if DataBaseConfig.db_type == 'postgresql':
                # PostgreSQL: ON CONFLICT DO NOTHING
                if unique_key_fields:
                    # 检查表是否有对应的唯一约束
                    logger.debug(f'检查表 {table_name} 在字段 {unique_key_fields} 上是否有唯一约束')
                    has_unique_constraint = await cls._check_unique_constraint_exists(db, table_name, unique_key_fields)
                    logger.debug(f'表 {table_name} 唯一约束检查结果: {has_unique_constraint}')
                    
                    if not has_unique_constraint:
                        logger.warning(
                            f'表 {table_name} 在字段 {unique_key_fields} 上没有唯一约束，'
                            f'无法使用 ON CONFLICT。将使用普通 INSERT 模式（可能因重复数据报错）'
                        )
                        # 降级为普通 INSERT
                        col_names = ', '.join([f'"{col}"' for col in all_columns])
                        placeholders = ', '.join([f':{col}' for col in all_columns])
                        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
                    else:
                        # 记录尝试插入的数据的唯一键值（用于日志）
                        if values_list and len(values_list) > 0:
                            sample_keys = []
                            for i, row_dict in enumerate(values_list[:5]):  # 只记录前5条
                                key_values = {k: row_dict.get(k) for k in unique_key_fields if k in row_dict}
                                if key_values:
                                    sample_keys.append(key_values)
                            if sample_keys:
                                logger.debug(f'尝试插入数据到表 {table_name}，唯一键字段: {unique_key_fields}，示例数据: {sample_keys}')
                        
                        # 需要指定冲突的列
                        conflict_cols = ', '.join([f'"{col}"' for col in unique_key_fields])
                        col_names = ', '.join([f'"{col}"' for col in all_columns])
                        placeholders = ', '.join([f':{col}' for col in all_columns])
                        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders}) ON CONFLICT ({conflict_cols}) DO NOTHING'
                        logger.debug(f'使用 ON CONFLICT 模式，冲突列: {conflict_cols}')
                else:
                    # 如果没有唯一键，使用普通 INSERT（PostgreSQL 没有 INSERT IGNORE）
                    logger.warning(f'表 {table_name} 没有唯一键字段，INSERT_IGNORE 模式将使用普通 INSERT')
                    col_names = ', '.join([f'"{col}"' for col in all_columns])
                    placeholders = ', '.join([f':{col}' for col in all_columns])
                    insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
            else:
                # MySQL: INSERT IGNORE
                col_names = ', '.join([f'`{col}`' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                insert_sql = f'INSERT IGNORE INTO `{table_name}` ({col_names}) VALUES ({placeholders})'
            
            total_rows = len(values_list)
            try:
                result = await db.execute(text(insert_sql), values_list)
                await db.flush()
                inserted_rows = result.rowcount if hasattr(result, 'rowcount') and result.rowcount is not None else total_rows
            except Exception as insert_error:
                # 如果 INSERT 失败（可能是因为没有唯一约束但使用了 ON CONFLICT），降级为普通 INSERT
                error_msg = str(insert_error)
                if 'ON CONFLICT' in insert_sql and ('没有匹配ON CONFLICT说明的唯一或者排除约束' in error_msg or 'no matching unique or exclusion constraint' in error_msg.lower()):
                    logger.warning(
                        f'表 {table_name} 使用 ON CONFLICT 失败（表上可能没有唯一约束），'
                        f'降级为普通 INSERT 模式重试'
                    )
                    # 降级为普通 INSERT
                    col_names = ', '.join([f'"{col}"' for col in all_columns])
                    placeholders = ', '.join([f':{col}' for col in all_columns])
                    insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
                    result = await db.execute(text(insert_sql), values_list)
                    await db.flush()
                    inserted_rows = len(values_list)
                else:
                    # 其他错误，直接抛出
                    raise
            
            # 记录冲突统计
            if unique_key_fields and total_rows > inserted_rows:
                skipped_count = total_rows - inserted_rows
                logger.warning(f'表 {table_name} INSERT_IGNORE 模式：尝试插入 {total_rows} 条，实际插入 {inserted_rows} 条，跳过 {skipped_count} 条重复数据（唯一键: {unique_key_fields}）')
                
                # 如果跳过的数据较多，记录更多详细信息
                if skipped_count > 0 and values_list:
                    # 记录所有唯一键值，帮助用户识别重复数据
                    all_key_values = []
                    for row_dict in values_list:
                        key_values = {k: row_dict.get(k) for k in unique_key_fields if k in row_dict}
                        if key_values:
                            all_key_values.append(key_values)
                    
                    # 记录前10条唯一键值
                    sample_count = min(10, len(all_key_values))
                    logger.debug(f'表 {table_name} 尝试插入的数据的唯一键值（前{sample_count}条）: {all_key_values[:sample_count]}')
            
            return inserted_rows

        elif update_mode == '2':
            # UPSERT: 存在则更新，不存在则插入
            if not unique_key_fields:
                raise ValueError('UPSERT 模式需要唯一键字段')
            
            # 记录尝试插入的数据的唯一键值（用于日志）
            if values_list and len(values_list) > 0:
                sample_keys = []
                for i, row_dict in enumerate(values_list[:5]):  # 只记录前5条
                    key_values = {k: row_dict.get(k) for k in unique_key_fields if k in row_dict}
                    if key_values:
                        sample_keys.append(key_values)
                if sample_keys:
                    logger.debug(f'尝试 UPSERT 数据到表 {table_name}，唯一键字段: {unique_key_fields}，示例数据: {sample_keys}')
            
            if DataBaseConfig.db_type == 'postgresql':
                # PostgreSQL: ON CONFLICT DO UPDATE
                conflict_cols = ', '.join([f'"{col}"' for col in unique_key_fields])
                col_names = ', '.join([f'"{col}"' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                # 构建 UPDATE SET 子句（排除唯一键字段）
                update_cols = [col for col in all_columns if col not in unique_key_fields]
                update_set = ', '.join([f'"{col}" = EXCLUDED."{col}"' for col in update_cols])
                insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {update_set}'
            else:
                # MySQL: ON DUPLICATE KEY UPDATE
                col_names = ', '.join([f'`{col}`' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                # 构建 UPDATE SET 子句（排除唯一键字段）
                update_cols = [col for col in all_columns if col not in unique_key_fields]
                update_set = ', '.join([f'`{col}` = VALUES(`{col}`)' for col in update_cols])
                insert_sql = f'INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders}) ON DUPLICATE KEY UPDATE {update_set}'
            
            total_rows = len(values_list)
            result = await db.execute(text(insert_sql), values_list)
            await db.flush()
            
            # 对于 UPSERT，PostgreSQL 不直接返回插入/更新的行数，但我们可以记录
            logger.info(f'表 {table_name} UPSERT 模式：处理 {total_rows} 条数据（唯一键: {unique_key_fields}），已存在的数据将被更新，不存在的数据将被插入')
            
            return total_rows

        elif update_mode == '3':
            # DELETE_INSERT: 先删除再插入
            if not unique_key_fields:
                raise ValueError('DELETE_INSERT 模式需要唯一键字段')
            
            # 从 DataFrame 中提取唯一键的值
            unique_key_values = []
            for idx, row in df.iterrows():
                key_dict = {}
                for key_field in unique_key_fields:
                    # 查找对应的 DataFrame 列
                    found = False
                    for orig_col, safe_col in col_mapping.items():
                        if safe_col == key_field:
                            value = row[orig_col]
                            if pd.isna(value):
                                key_dict[key_field] = None
                            else:
                                key_dict[key_field] = value
                            found = True
                            break
                    if not found:
                        # 如果找不到，可能是系统列
                        if key_field in system_columns:
                            if key_field == 'task_id':
                                key_dict[key_field] = task_id
                            elif key_field == 'config_id':
                                key_dict[key_field] = config_id
                            elif key_field == 'api_code':
                                key_dict[key_field] = api_code
                            elif key_field == 'download_date':
                                key_dict[key_field] = download_date
                if key_dict:
                    unique_key_values.append(key_dict)
            
            # 构建 DELETE 语句
            if unique_key_values:
                if DataBaseConfig.db_type == 'postgresql':
                    # PostgreSQL: 使用 IN 子句或 OR 条件
                    delete_conditions = []
                    for key_dict in unique_key_values:
                        conditions = []
                        for key_field, key_value in key_dict.items():
                            if key_value is None:
                                conditions.append(f'"{key_field}" IS NULL')
                            else:
                                conditions.append(f'"{key_field}" = :{key_field}_{len(delete_conditions)}')
                        delete_conditions.append('(' + ' AND '.join(conditions) + ')')
                    
                    # 简化：使用 IN 子句（如果唯一键是单个字段）
                    if len(unique_key_fields) == 1:
                        key_field = unique_key_fields[0]
                        key_values = [kv[key_field] for kv in unique_key_values if key_field in kv]
                        if key_values:
                            placeholders = ', '.join([f':val_{i}' for i in range(len(key_values))])
                            delete_sql = f'DELETE FROM "{table_name}" WHERE "{key_field}" IN ({placeholders})'
                            delete_params = {f'val_{i}': val for i, val in enumerate(key_values)}
                            await db.execute(text(delete_sql), delete_params)
                    else:
                        # 多个字段的唯一键，需要逐个删除
                        for key_dict in unique_key_values:
                            conditions = []
                            delete_params = {}
                            for idx, (key_field, key_value) in enumerate(key_dict.items()):
                                if key_value is None:
                                    conditions.append(f'"{key_field}" IS NULL')
                                else:
                                    param_name = f'key_{idx}'
                                    conditions.append(f'"{key_field}" = :{param_name}')
                                    delete_params[param_name] = key_value
                            delete_sql = f'DELETE FROM "{table_name}" WHERE ' + ' AND '.join(conditions)
                            await db.execute(text(delete_sql), delete_params)
                else:
                    # MySQL: 使用 IN 子句
                    if len(unique_key_fields) == 1:
                        key_field = unique_key_fields[0]
                        key_values = [kv[key_field] for kv in unique_key_values if key_field in kv]
                        if key_values:
                            placeholders = ', '.join([f':val_{i}' for i in range(len(key_values))])
                            delete_sql = f'DELETE FROM `{table_name}` WHERE `{key_field}` IN ({placeholders})'
                            delete_params = {f'val_{i}': val for i, val in enumerate(key_values)}
                            await db.execute(text(delete_sql), delete_params)
                    else:
                        # 多个字段的唯一键，需要逐个删除
                        for key_dict in unique_key_values:
                            conditions = []
                            delete_params = {}
                            for idx, (key_field, key_value) in enumerate(key_dict.items()):
                                if key_value is None:
                                    conditions.append(f'`{key_field}` IS NULL')
                                else:
                                    param_name = f'key_{idx}'
                                    conditions.append(f'`{key_field}` = :{param_name}')
                                    delete_params[param_name] = key_value
                            delete_sql = f'DELETE FROM `{table_name}` WHERE ' + ' AND '.join(conditions)
                            await db.execute(text(delete_sql), delete_params)
                
                await db.flush()
            
            # 执行普通 INSERT
            if DataBaseConfig.db_type == 'postgresql':
                col_names = ', '.join([f'"{col}"' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders})'
            else:
                col_names = ', '.join([f'`{col}`' for col in all_columns])
                placeholders = ', '.join([f':{col}' for col in all_columns])
                insert_sql = f'INSERT INTO `{table_name}` ({col_names}) VALUES ({placeholders})'
            
            result = await db.execute(text(insert_sql), values_list)
            await db.flush()
            return len(values_list)

        else:
            raise ValueError(f'不支持的更新模式: {update_mode}')

    @classmethod
    async def add_data_batch_to_table_dao(
        cls, db: AsyncSession, table_name: str, data_list: list[dict]
    ) -> int:
        """
        批量新增数据到指定表（使用动态表名）

        :param db: orm对象
        :param table_name: 表名（需要验证，防止SQL注入）
        :param data_list: 数据字典列表
        :return: 插入的记录数
        """
        from sqlalchemy import text, inspect
        from config.env import DataBaseConfig
        import json
        import re

        if not data_list:
            return 0

        # 验证表名，只允许字母、数字和下划线
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f'无效的表名: {table_name}')

        # 根据数据库类型选择不同的插入方式
        if DataBaseConfig.db_type == 'postgresql':
            # PostgreSQL 使用 JSONB，表名需要用双引号转义
            # 使用命名参数，SQLAlchemy 会自动转换为 PostgreSQL 的位置参数
            insert_sql = f"""
                INSERT INTO "{table_name}" (task_id, config_id, api_code, download_date, data_content, create_time)
                VALUES (:task_id, :config_id, :api_code, :download_date, CAST(:data_content AS JSONB), :create_time)
            """
        else:
            # MySQL 使用 JSON，表名用反引号转义
            insert_sql = f"""
                INSERT INTO `{table_name}` (task_id, config_id, api_code, download_date, data_content, create_time)
                VALUES (:task_id, :config_id, :api_code, :download_date, :data_content, :create_time)
            """

        # 准备批量插入数据（统一使用字典列表）
        values_list = []
        for data in data_list:
            # 将字典转换为 JSON 字符串
            data_content = json.dumps(data['data_content'], ensure_ascii=False)
            
            values_list.append({
                'task_id': data['task_id'],
                'config_id': data['config_id'],
                'api_code': data['api_code'],
                'download_date': data['download_date'],
                'data_content': data_content,
                'create_time': data['create_time']
            })

        # 执行批量插入
        result = await db.execute(text(insert_sql), values_list)
        await db.flush()
        return len(values_list)

    @classmethod
    async def delete_data_dao(cls, db: AsyncSession, data_ids: list[int]) -> int:
        """
        删除数据

        :param db: orm对象
        :param data_ids: 数据ID列表
        :return: 删除数量
        """
        result = await db.execute(delete(TushareData).where(TushareData.data_id.in_(data_ids)))
        return result.rowcount

    @classmethod
    async def clear_data_dao(cls, db: AsyncSession) -> int:
        """
        清空所有数据

        :param db: orm对象
        :return: 删除结果
        """
        result = await db.execute(delete(TushareData))
        return result.rowcount


class TushareWorkflowConfigDao:
    """
    Tushare流程配置管理模块数据库操作层
    """

    @classmethod
    async def get_workflow_detail_by_id(cls, db: AsyncSession, workflow_id: int) -> TushareWorkflowConfig | None:
        """
        根据流程ID获取流程详细信息

        :param db: orm对象
        :param workflow_id: 流程ID
        :return: 流程信息对象
        """
        workflow_info = (
            await db.execute(select(TushareWorkflowConfig).where(TushareWorkflowConfig.workflow_id == workflow_id))
        ).scalars().first()

        return workflow_info

    @classmethod
    async def get_workflow_detail_by_info(
        cls, db: AsyncSession, workflow: TushareWorkflowConfigModel
    ) -> TushareWorkflowConfig | None:
        """
        根据流程参数获取流程信息

        :param db: orm对象
        :param workflow: 流程参数对象
        :return: 流程信息对象
        """
        workflow_info = (
            (
                await db.execute(
                    select(TushareWorkflowConfig).where(
                        TushareWorkflowConfig.workflow_name == workflow.workflow_name,
                    )
                )
            )
            .scalars()
            .first()
        )

        return workflow_info

    @classmethod
    async def get_workflow_list(
        cls, db: AsyncSession, query_object: TushareWorkflowConfigPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取流程列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 流程列表信息对象
        """
        query = (
            select(TushareWorkflowConfig)
            .where(
                TushareWorkflowConfig.workflow_name.like(f'%{query_object.workflow_name}%')
                if query_object.workflow_name
                else True,
                TushareWorkflowConfig.status == query_object.status if query_object.status else True,
            )
            .order_by(TushareWorkflowConfig.workflow_id)
            .distinct()
        )

        workflow_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return workflow_list

    @classmethod
    async def add_workflow_dao(cls, db: AsyncSession, workflow: TushareWorkflowConfigModel) -> TushareWorkflowConfig:
        """
        新增流程信息

        :param db: orm对象
        :param workflow: 流程对象
        :return: 流程对象
        """
        db_workflow = TushareWorkflowConfig(**workflow.model_dump(exclude={'workflow_id'}))
        db.add(db_workflow)
        await db.flush()
        await db.refresh(db_workflow)
        return db_workflow

    @classmethod
    async def edit_workflow_dao(
        cls,
        db: AsyncSession,
        workflow_id_or_model: int | TushareWorkflowConfigModel,
        workflow_dict: dict[str, Any] | None = None,
    ) -> int:
        """
        编辑流程信息

        :param db: orm对象
        :param workflow_id_or_model: 流程ID（int）或流程模型对象（TushareWorkflowConfigModel）
        :param workflow_dict: 流程字段字典（snake_case格式），当第一个参数是workflow_id时使用
        :return: 编辑结果
        """
        # 兼容两种调用方式：
        # 1) edit_workflow_dao(db, workflow_model)
        # 2) edit_workflow_dao(db, workflow_id, workflow_dict)
        if isinstance(workflow_id_or_model, TushareWorkflowConfigModel):
            workflow = workflow_id_or_model
            workflow_id = workflow.workflow_id
            if workflow_id is None:
                raise ValueError('workflow_id不能为None')
            # 使用 by_alias=False 获取 snake_case 字段名，exclude_none=True 只更新有值的字段
            workflow_dict = workflow.model_dump(exclude={'workflow_id'}, exclude_none=True, by_alias=False)
        else:
            workflow_id = workflow_id_or_model
            if workflow_dict is None:
                raise ValueError('当使用workflow_id时，必须提供workflow_dict参数')

        # 从字典中移除 workflow_id，因为它只用于 WHERE 条件
        update_dict = {k: v for k, v in workflow_dict.items() if k != 'workflow_id'}

        await db.execute(
            update(TushareWorkflowConfig)
            .where(TushareWorkflowConfig.workflow_id == workflow_id)
            .values(**update_dict)
        )
        return workflow_id

    @classmethod
    async def delete_workflow_dao(cls, db: AsyncSession, workflow_ids: Sequence[int]) -> int:
        """
        删除流程信息

        :param db: orm对象
        :param workflow_ids: 流程ID列表
        :return: 删除结果
        """
        result = await db.execute(
            delete(TushareWorkflowConfig).where(TushareWorkflowConfig.workflow_id.in_(workflow_ids))
        )
        return result.rowcount


class TushareWorkflowStepDao:
    """
    Tushare流程步骤管理模块数据库操作层
    """

    @classmethod
    async def get_step_detail_by_id(cls, db: AsyncSession, step_id: int) -> TushareWorkflowStep | None:
        """
        根据步骤ID获取步骤详细信息

        :param db: orm对象
        :param step_id: 步骤ID
        :return: 步骤信息对象
        """
        step_info = (
            await db.execute(select(TushareWorkflowStep).where(TushareWorkflowStep.step_id == step_id))
        ).scalars().first()

        return step_info

    @classmethod
    async def get_steps_by_workflow_id(cls, db: AsyncSession, workflow_id: int) -> list[TushareWorkflowStep]:
        """
        根据流程ID获取所有步骤

        :param db: orm对象
        :param workflow_id: 流程ID
        :return: 步骤列表
        """
        steps = (
            await db.execute(
                select(TushareWorkflowStep)
                .where(TushareWorkflowStep.workflow_id == workflow_id)
                .order_by(TushareWorkflowStep.step_order)
            )
        ).scalars().all()

        return list(steps)

    @classmethod
    async def get_step_list(
        cls, db: AsyncSession, query_object: TushareWorkflowStepPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取步骤列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 步骤列表信息对象
        """
        query = (
            select(TushareWorkflowStep)
            .where(
                TushareWorkflowStep.workflow_id == query_object.workflow_id if query_object.workflow_id else True,
                TushareWorkflowStep.step_name.like(f'%{query_object.step_name}%') if query_object.step_name else True,
                TushareWorkflowStep.config_id == query_object.config_id if query_object.config_id else True,
                TushareWorkflowStep.status == query_object.status if query_object.status else True,
            )
            .order_by(TushareWorkflowStep.workflow_id, TushareWorkflowStep.step_order)
        )

        step_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return step_list

    @classmethod
    async def add_step_dao(cls, db: AsyncSession, step: TushareWorkflowStepModel) -> TushareWorkflowStep:
        """
        新增步骤信息

        :param db: orm对象
        :param step: 步骤对象
        :return: 步骤对象
        """
        db_step = TushareWorkflowStep(**step.model_dump(exclude={'step_id'}))
        db.add(db_step)
        await db.flush()
        await db.refresh(db_step)
        return db_step

    @classmethod
    async def edit_step_dao(cls, db: AsyncSession, step: TushareWorkflowStepModel) -> int:
        """
        编辑步骤信息

        :param db: orm对象
        :param step: 步骤对象
        :return: 编辑结果
        """
        # 获取步骤字典，但确保 step_params 字段即使为 None 也要包含
        # 先获取包含所有字段的字典（不排除 None）
        step_dict_all = step.model_dump(exclude={'step_id'}, exclude_none=False)
        # 然后获取排除 None 的字典（用于其他字段）
        step_dict = step.model_dump(exclude={'step_id'}, exclude_none=True)
        
        # 对于 step_params 字段，即使为 None 也要包含（允许清空参数）
        # 从完整字典中获取 step_params，确保即使为 None 也会被包含
        if 'step_params' in step_dict_all:
            step_dict['step_params'] = step_dict_all['step_params']
        
        await db.execute(
            update(TushareWorkflowStep)
            .where(TushareWorkflowStep.step_id == step.step_id)
            .values(**step_dict)
        )
        return step.step_id

    @classmethod
    async def delete_step_dao(cls, db: AsyncSession, step_ids: Sequence[int]) -> int:
        """
        删除步骤信息

        :param db: orm对象
        :param step_ids: 步骤ID列表
        :return: 删除结果
        """
        result = await db.execute(delete(TushareWorkflowStep).where(TushareWorkflowStep.step_id.in_(step_ids)))
        return result.rowcount

    @classmethod
    async def delete_steps_by_workflow_id(cls, db: AsyncSession, workflow_id: int) -> int:
        """
        根据流程ID删除所有步骤

        :param db: orm对象
        :param workflow_id: 流程ID
        :return: 删除结果
        """
        result = await db.execute(delete(TushareWorkflowStep).where(TushareWorkflowStep.workflow_id == workflow_id))
        return result.rowcount
