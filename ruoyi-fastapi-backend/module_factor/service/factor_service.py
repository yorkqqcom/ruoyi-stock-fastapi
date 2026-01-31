from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from module_factor.dao.factor_dao import FactorCalcLogDao, FactorDefinitionDao, FactorTaskDao, FactorValueDao
from module_factor.entity.vo.factor_vo import (
    DeleteFactorDefinitionModel,
    DeleteFactorTaskModel,
    EditFactorDefinitionModel,
    EditFactorTaskModel,
    FactorCalcLogPageQueryModel,
    FactorDefinitionModel,
    FactorDefinitionPageQueryModel,
    FactorTaskModel,
    FactorTaskPageQueryModel,
    FactorValueQueryModel,
)
from module_factor.service.factor_scheduler_service import FactorSchedulerService
from module_factor.task.factor_calc_task import run_factor_task_sync
from utils.log_util import logger
import threading


class FactorDefinitionService:
    """
    因子定义管理服务
    """

    @classmethod
    async def get_definition_list_services(
        cls, db: AsyncSession, query_model: FactorDefinitionPageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        return await FactorDefinitionDao.get_definition_list(db, query_model, is_page)

    @classmethod
    async def add_definition_services(
        cls, db: AsyncSession, model: FactorDefinitionModel
    ) -> CrudResponseModel:
        model.validate_fields()
        exist = await FactorDefinitionDao.get_definition_by_code(db, model.factor_code or '')
        if exist:
            return CrudResponseModel(is_success=False, message='因子代码已存在')

        await FactorDefinitionDao.add_definition_dao(db, model)
        await db.commit()
        return CrudResponseModel(is_success=True, message='新增因子定义成功')

    @classmethod
    async def edit_definition_services(
        cls, db: AsyncSession, model: EditFactorDefinitionModel
    ) -> CrudResponseModel:
        if not model.id:
            return CrudResponseModel(is_success=False, message='因子ID不能为空')
        await FactorDefinitionDao.edit_definition_dao(db, model)
        await db.commit()
        return CrudResponseModel(is_success=True, message='编辑因子定义成功')

    @classmethod
    async def delete_definition_services(
        cls, db: AsyncSession, model: DeleteFactorDefinitionModel
    ) -> CrudResponseModel:
        await FactorDefinitionDao.delete_definitions_dao(db, model)
        await db.commit()
        return CrudResponseModel(is_success=True, message='删除因子定义成功')


class FactorTaskService:
    """
    因子任务管理服务
    """

    @classmethod
    async def get_task_list_services(
        cls, db: AsyncSession, query_model: FactorTaskPageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        return await FactorTaskDao.get_task_list(db, query_model, is_page)

    @classmethod
    async def add_task_services(cls, db: AsyncSession, model: FactorTaskModel) -> CrudResponseModel:
        model.validate_fields()
        db_obj = await FactorTaskDao.add_task_dao(db, model)
        await db.commit()

        # 注册调度
        vo_model = FactorTaskModel.model_validate(db_obj, from_attributes=True)
        FactorSchedulerService.register_task_scheduler(vo_model)
        logger.info(f'新增因子任务并注册调度成功: {vo_model.task_name}')

        return CrudResponseModel(is_success=True, message='新增因子任务成功')

    @classmethod
    async def edit_task_services(cls, db: AsyncSession, model: EditFactorTaskModel) -> CrudResponseModel:
        if not model.id:
            return CrudResponseModel(is_success=False, message='任务ID不能为空')

        old_do = await FactorTaskDao.get_task_by_id(db, model.id)
        if not old_do:
            return CrudResponseModel(is_success=False, message='任务不存在')

        old_model = FactorTaskModel.model_validate(old_do, from_attributes=True)

        await FactorTaskDao.edit_task_dao(db, model)
        await db.commit()

        new_do = await FactorTaskDao.get_task_by_id(db, model.id)
        if new_do:
            new_model = FactorTaskModel.model_validate(new_do, from_attributes=True)
            FactorSchedulerService.update_task_scheduler(new_model, old_model)
        logger.info(f'编辑因子任务并更新调度成功: {model.task_name}')

        return CrudResponseModel(is_success=True, message='编辑因子任务成功')

    @classmethod
    async def change_task_status_services(
        cls, db: AsyncSession, task_id: int, status: str
    ) -> CrudResponseModel:
        task_do = await FactorTaskDao.get_task_by_id(db, task_id)
        if not task_do:
            return CrudResponseModel(is_success=False, message='任务不存在')

        await FactorTaskDao.update_task_status_dao(db, task_id, status)
        await db.commit()

        updated_do = await FactorTaskDao.get_task_by_id(db, task_id)
        if updated_do:
            updated_model = FactorTaskModel.model_validate(updated_do, from_attributes=True)
            old_model = FactorTaskModel.model_validate(task_do, from_attributes=True)
            FactorSchedulerService.update_task_scheduler(updated_model, old_model)

        return CrudResponseModel(is_success=True, message='修改任务状态成功')

    @classmethod
    async def delete_task_services(cls, db: AsyncSession, model: DeleteFactorTaskModel) -> CrudResponseModel:
        ids = [int(x) for x in model.task_ids.split(',') if x]
        for task_id in ids:
            FactorSchedulerService.remove_task_scheduler(task_id)

        await FactorTaskDao.delete_tasks_dao(db, model)
        await db.commit()
        return CrudResponseModel(is_success=True, message='删除因子任务成功')

    @classmethod
    async def execute_task_services(cls, db: AsyncSession, task_id: int) -> CrudResponseModel:
        """
        手动触发因子任务执行（在后台线程中运行）
        """
        task_do = await FactorTaskDao.get_task_by_id(db, task_id)
        if not task_do:
            return CrudResponseModel(is_success=False, message='任务不存在')

        def _run() -> None:
            try:
                run_factor_task_sync(task_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception('执行因子任务(ID=%s) 失败: %s', task_id, exc)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

        return CrudResponseModel(is_success=True, message='因子任务已提交后台执行')


class FactorValueService:
    """
    因子结果查询服务
    """

    @classmethod
    async def get_factor_value_page_services(
        cls, db: AsyncSession, query_model: FactorValueQueryModel
    ) -> PageModel | list[dict[str, Any]]:
        return await FactorValueDao.query_values(db, query_model, is_page=True)


class FactorCalcLogService:
    """
    因子计算日志管理服务
    """

    @classmethod
    async def get_log_list_services(
        cls, db: AsyncSession, query_model: FactorCalcLogPageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        """
        获取因子计算日志列表信息service

        :param db: orm对象
        :param query_model: 查询参数对象
        :param is_page: 是否开启分页
        :return: 因子计算日志列表信息对象
        """
        return await FactorCalcLogDao.get_log_list(db, query_model, is_page)

