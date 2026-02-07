from collections.abc import Sequence
from typing import Any

from datetime import datetime, time

from sqlalchemy import Select, and_, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_factor.entity.do.factor_do import (
    FactorCalcLog,
    FactorDefinition,
    FactorTask,
    FactorValue,
    ModelPredictResult,
    ModelSceneBinding,
    ModelTrainResult,
    ModelTrainTask,
)
from module_factor.entity.vo.factor_vo import (
    DeleteFactorDefinitionModel,
    DeleteFactorTaskModel,
    EditModelTrainTaskModel,
    FactorCalcLogPageQueryModel,
    FactorDefinitionModel,
    FactorDefinitionPageQueryModel,
    FactorTaskModel,
    FactorTaskPageQueryModel,
    FactorValueQueryModel,
    ModelPredictResultPageQueryModel,
    ModelTrainResultPageQueryModel,
    ModelTrainTaskModel,
    ModelTrainTaskPageQueryModel,
)
from utils.common_util import CamelCaseUtil
from utils.page_util import PageUtil
from utils.log_util import logger


class FactorDefinitionDao:
    """
    因子定义管理模块数据库操作层
    """

    @classmethod
    async def get_definition_by_id(cls, db: AsyncSession, factor_id: int) -> FactorDefinition | None:
        return (await db.execute(select(FactorDefinition).where(FactorDefinition.id == factor_id))).scalars().first()

    @classmethod
    async def get_definition_by_code(cls, db: AsyncSession, factor_code: str) -> FactorDefinition | None:
        return (
            await db.execute(select(FactorDefinition).where(FactorDefinition.factor_code == factor_code))
        ).scalars().first()

    @classmethod
    def _build_definition_query(
        cls, query_object: FactorDefinitionPageQueryModel
    ) -> Select[tuple[FactorDefinition]]:
        return (
            select(FactorDefinition)
            .where(
                FactorDefinition.factor_code.like(f'%{query_object.factor_code}%')
                if query_object.factor_code
                else True,
                FactorDefinition.factor_name.like(f'%{query_object.factor_name}%')
                if query_object.factor_name
                else True,
                FactorDefinition.category == query_object.category if query_object.category else True,
                FactorDefinition.enable_flag == query_object.enable_flag if query_object.enable_flag else True,
            )
            .order_by(FactorDefinition.id)
            .distinct()
        )

    @classmethod
    async def get_definition_list(
        cls, db: AsyncSession, query_object: FactorDefinitionPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = cls._build_definition_query(query_object)
        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return result

    @classmethod
    async def add_definition_dao(cls, db: AsyncSession, model: FactorDefinitionModel) -> FactorDefinition:
        db_obj = FactorDefinition(**model.model_dump(exclude={'id'}))
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @classmethod
    async def edit_definition_dao(cls, db: AsyncSession, model: FactorDefinitionModel) -> int:
        update_dict = model.model_dump(exclude={'id'}, exclude_unset=True)
        if not update_dict or model.id is None:
            return 0
        stmt = (
            update(FactorDefinition)
            .where(FactorDefinition.id == model.id)
            .values(**update_dict)
        )
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def delete_definitions_dao(cls, db: AsyncSession, model: DeleteFactorDefinitionModel) -> int:
        ids = [int(x) for x in model.factor_ids.split(',') if x]
        stmt = delete(FactorDefinition).where(FactorDefinition.id.in_(ids))
        result = await db.execute(stmt)
        return result.rowcount or 0


class FactorTaskDao:
    """
    因子计算任务管理模块数据库操作层
    """

    @classmethod
    async def get_task_by_id(cls, db: AsyncSession, task_id: int) -> FactorTask | None:
        return (await db.execute(select(FactorTask).where(FactorTask.id == task_id))).scalars().first()

    @classmethod
    def _build_task_query(cls, query_object: FactorTaskPageQueryModel) -> Select[tuple[FactorTask]]:
        return (
            select(FactorTask)
            .where(
                FactorTask.task_name.like(f'%{query_object.task_name}%')
                if query_object.task_name
                else True,
                FactorTask.freq == query_object.freq if query_object.freq else True,
                FactorTask.status == query_object.status if query_object.status else True,
            )
            .order_by(FactorTask.id)
            .distinct()
        )

    @classmethod
    async def get_task_list(
        cls, db: AsyncSession, query_object: FactorTaskPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = cls._build_task_query(query_object)
        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return result

    @classmethod
    async def add_task_dao(cls, db: AsyncSession, model: FactorTaskModel) -> FactorTask:
        db_obj = FactorTask(**model.model_dump(exclude={'id'}))
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @classmethod
    async def edit_task_dao(cls, db: AsyncSession, model: FactorTaskModel) -> int:
        update_dict = model.model_dump(exclude={'id'}, exclude_unset=True)
        if not update_dict or model.id is None:
            return 0
        stmt = update(FactorTask).where(FactorTask.id == model.id).values(**update_dict)
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def update_task_status_dao(cls, db: AsyncSession, task_id: int, status: str) -> int:
        stmt = update(FactorTask).where(FactorTask.id == task_id).values(status=status)
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def update_task_run_stats_dao(
        cls, db: AsyncSession, task_id: int, is_success: bool, last_run_time: datetime | None = None
    ) -> int:
        """
        更新任务运行统计信息

        :param db: orm对象
        :param task_id: 任务ID
        :param is_success: 是否成功
        :param last_run_time: 最后运行时间
        :return: 更新的行数
        """
        from sqlalchemy import func

        # 获取当前任务信息
        task = await cls.get_task_by_id(db, task_id)
        if not task:
            return 0

        # 计算新的统计值
        run_count = (task.run_count or 0) + 1
        success_count = (task.success_count or 0) + (1 if is_success else 0)
        fail_count = (task.fail_count or 0) + (0 if is_success else 1)
        update_time = last_run_time or datetime.now()

        stmt = (
            update(FactorTask)
            .where(FactorTask.id == task_id)
            .values(
                run_count=run_count,
                success_count=success_count,
                fail_count=fail_count,
                last_run_time=update_time,
            )
        )
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def delete_tasks_dao(cls, db: AsyncSession, model: DeleteFactorTaskModel) -> int:
        ids = [int(x) for x in model.task_ids.split(',') if x]
        stmt = delete(FactorTask).where(FactorTask.id.in_(ids))
        result = await db.execute(stmt)
        return result.rowcount or 0


class FactorValueDao:
    """
    因子结果数据访问层
    """

    @classmethod
    async def bulk_insert_values_dao(cls, db: AsyncSession, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        db_objects = [FactorValue(**record) for record in records]
        db.add_all(db_objects)
        await db.flush()

    @classmethod
    async def query_values(
        cls, db: AsyncSession, query_object: FactorValueQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        """
        查询因子结果，支持分页
        """
        factor_codes: list[str] | None = None
        if query_object.factor_codes:
            factor_codes = [code.strip() for code in query_object.factor_codes.split(',') if code.strip()]

        query = (
            select(FactorValue)
            .where(
                FactorValue.symbol == query_object.symbol if query_object.symbol else True,
                FactorValue.trade_date >= query_object.start_date if query_object.start_date else True,
                FactorValue.trade_date <= query_object.end_date if query_object.end_date else True,
                FactorValue.factor_code.in_(factor_codes) if factor_codes else True,
            )
            .order_by(FactorValue.trade_date, FactorValue.symbol, FactorValue.factor_code)
            .distinct()
        )

        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        if isinstance(result, PageModel):
            result.rows = CamelCaseUtil.transform_result(result.rows)
        else:
            result = CamelCaseUtil.transform_result(result)
        return result


class FactorCalcLogDao:
    """
    因子计算日志数据访问层
    """

    @classmethod
    async def add_log_dao(cls, db: AsyncSession, log: FactorCalcLog) -> None:
        db.add(log)
        await db.flush()

    @classmethod
    async def list_logs_by_task(cls, db: AsyncSession, task_id: int) -> Sequence[dict[str, Any]]:
        logs = (await db.execute(select(FactorCalcLog).where(FactorCalcLog.task_id == task_id))).scalars().all()
        return CamelCaseUtil.transform_result(logs)

    @classmethod
    async def get_log_list(
        cls, db: AsyncSession, query_object: FactorCalcLogPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        """
        根据查询参数获取因子计算日志列表信息

        :param db: orm对象
        :param query_object: 查询参数对象
        :param is_page: 是否开启分页
        :return: 因子计算日志列表信息对象
        """
        query = (
            select(FactorCalcLog)
            .where(
                FactorCalcLog.task_id == query_object.task_id if query_object.task_id else True,
                FactorCalcLog.task_name.like(f'%{query_object.task_name}%')
                if query_object.task_name
                else True,
                FactorCalcLog.status == query_object.status if query_object.status else True,
                FactorCalcLog.create_time.between(
                    datetime.combine(datetime.strptime(query_object.begin_time, '%Y-%m-%d'), time(00, 00, 00)),
                    datetime.combine(datetime.strptime(query_object.end_time, '%Y-%m-%d'), time(23, 59, 59)),
                )
                if query_object.begin_time and query_object.end_time
                else True,
            )
            .order_by(desc(FactorCalcLog.create_time))
            .distinct()
        )
        log_list: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )

        return log_list


# ==================== 模型训练相关 DAO ====================


class ModelTrainTaskDao:
    """
    模型训练任务管理模块数据库操作层
    """

    @classmethod
    async def get_task_by_id(cls, db: AsyncSession, task_id: int) -> ModelTrainTask | None:
        return (await db.execute(select(ModelTrainTask).where(ModelTrainTask.id == task_id))).scalars().first()

    @classmethod
    def _build_task_query(cls, query_object: ModelTrainTaskPageQueryModel) -> Select[tuple[ModelTrainTask]]:
        return (
            select(ModelTrainTask)
            .where(
                ModelTrainTask.task_name.like(f'%{query_object.task_name}%')
                if query_object.task_name
                else True,
                ModelTrainTask.status == query_object.status if query_object.status else True,
                ModelTrainTask.create_time.between(
                    datetime.combine(datetime.strptime(query_object.begin_time, '%Y-%m-%d'), time(00, 00, 00)),
                    datetime.combine(datetime.strptime(query_object.end_time, '%Y-%m-%d'), time(23, 59, 59)),
                )
                if query_object.begin_time and query_object.end_time
                else True,
            )
            .order_by(desc(ModelTrainTask.id))
            .distinct()
        )

    @classmethod
    async def get_task_list(
        cls, db: AsyncSession, query_object: ModelTrainTaskPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = cls._build_task_query(query_object)
        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return result

    @classmethod
    async def add_task_dao(cls, db: AsyncSession, model: ModelTrainTaskModel) -> ModelTrainTask:
        # 调试：确认入参 model 的字段与类型
        logger.info(
            '[add_task_dao] model type=%s, model.task_name=%r, model.factor_codes=%r, model.start_date=%r, model.end_date=%r',
            type(model).__name__,
            getattr(model, 'task_name', None),
            getattr(model, 'factor_codes', None),
            getattr(model, 'start_date', None),
            getattr(model, 'end_date', None),
        )
        # 显式按 ORM 列名构建字典，避免 model_dump 与 alias 导致字段丢失
        values = {
            'task_name': model.task_name,
            'factor_codes': model.factor_codes,
            'symbol_universe': model.symbol_universe,
            'start_date': model.start_date,
            'end_date': model.end_date,
            'model_params': model.model_params,
            'train_test_split': model.train_test_split,
            'status': model.status,
            'last_run_time': model.last_run_time,
            'run_count': model.run_count or 0,
            'success_count': model.success_count or 0,
            'fail_count': model.fail_count or 0,
            'remark': model.remark,
            'create_by': model.create_by,
            'create_time': model.create_time,
            'update_by': model.update_by,
            'update_time': model.update_time,
        }
        logger.info(
            '[add_task_dao] values keys=%s, values[task_name]=%r, values[factor_codes]=%r',
            list(values.keys()),
            values.get('task_name'),
            values.get('factor_codes'),
        )
        db_obj = ModelTrainTask(**values)
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        return db_obj

    @classmethod
    async def edit_task_dao(cls, db: AsyncSession, model: EditModelTrainTaskModel | ModelTrainTaskModel) -> int:
        # 确保 model 是 Pydantic 模型对象
        if isinstance(model, dict):
            model = EditModelTrainTaskModel(**model)
        
        update_dict = model.model_dump(exclude={'id'}, exclude_unset=True)
        if not update_dict or model.id is None:
            return 0
        stmt = update(ModelTrainTask).where(ModelTrainTask.id == model.id).values(**update_dict)
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def update_task_status_dao(cls, db: AsyncSession, task_id: int, status: str) -> int:
        stmt = update(ModelTrainTask).where(ModelTrainTask.id == task_id).values(status=status)
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def update_task_run_stats_dao(
        cls, db: AsyncSession, task_id: int, is_success: bool, last_run_time: datetime | None = None
    ) -> int:
        """
        更新任务运行统计信息

        :param db: orm对象
        :param task_id: 任务ID
        :param is_success: 是否成功
        :param last_run_time: 最后运行时间
        :return: 更新的行数
        """
        task = await cls.get_task_by_id(db, task_id)
        if not task:
            return 0

        run_count = (task.run_count or 0) + 1
        success_count = (task.success_count or 0) + (1 if is_success else 0)
        fail_count = (task.fail_count or 0) + (0 if is_success else 1)
        update_time = last_run_time or datetime.now()

        stmt = (
            update(ModelTrainTask)
            .where(ModelTrainTask.id == task_id)
            .values(
                run_count=run_count,
                success_count=success_count,
                fail_count=fail_count,
                last_run_time=update_time,
            )
        )
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def delete_tasks_dao(cls, db: AsyncSession, task_ids: str) -> int:
        ids = [int(x) for x in task_ids.split(',') if x]
        stmt = delete(ModelTrainTask).where(ModelTrainTask.id.in_(ids))
        result = await db.execute(stmt)
        return result.rowcount or 0


class ModelTrainResultDao:
    """
    模型训练结果数据访问层
    """

    @classmethod
    async def get_result_by_id(cls, db: AsyncSession, result_id: int) -> ModelTrainResult | None:
        return (await db.execute(select(ModelTrainResult).where(ModelTrainResult.id == result_id))).scalars().first()

    @classmethod
    def _build_result_query(cls, query_object: ModelTrainResultPageQueryModel) -> Select[tuple[ModelTrainResult]]:
        return (
            select(ModelTrainResult)
            .where(
                ModelTrainResult.task_id == query_object.task_id if query_object.task_id else True,
                ModelTrainResult.task_name.like(f'%{query_object.task_name}%')
                if query_object.task_name
                else True,
                ModelTrainResult.status == query_object.status if query_object.status else True,
                ModelTrainResult.create_time.between(
                    datetime.combine(datetime.strptime(query_object.begin_time, '%Y-%m-%d'), time(00, 00, 00)),
                    datetime.combine(datetime.strptime(query_object.end_time, '%Y-%m-%d'), time(23, 59, 59)),
                )
                if query_object.begin_time and query_object.end_time
                else True,
            )
            .order_by(desc(ModelTrainResult.create_time))
            .distinct()
        )

    @classmethod
    async def get_result_list(
        cls, db: AsyncSession, query_object: ModelTrainResultPageQueryModel, is_page: bool = False
    ) -> PageModel | list[dict[str, Any]]:
        query = cls._build_result_query(query_object)
        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        return result

    @classmethod
    async def add_result_dao(cls, db: AsyncSession, result: ModelTrainResult) -> ModelTrainResult:
        db.add(result)
        await db.flush()
        await db.refresh(result)
        return result

    @classmethod
    async def get_next_version_for_task(cls, db: AsyncSession, task_id: int) -> int:
        """
        获取指定任务的下一个模型版本号（同一任务内从1递增）
        """
        max_version = (
            await db.execute(
                select(func.max(ModelTrainResult.version)).where(ModelTrainResult.task_id == task_id)
            )
        ).scalars().first()
        return (int(max_version) if max_version is not None else 0) + 1

    @classmethod
    async def get_latest_success_result_by_task(
        cls, db: AsyncSession, task_id: int
    ) -> ModelTrainResult | None:
        """
        获取某个任务最新的训练成功结果（按版本号与创建时间倒序）
        """
        result = (
            await db.execute(
                select(ModelTrainResult)
                .where(
                    ModelTrainResult.task_id == task_id,
                    ModelTrainResult.status == '0',
                )
                .order_by(desc(ModelTrainResult.version), desc(ModelTrainResult.create_time))
                .limit(1)
            )
        ).scalars().first()
        return result


class ModelPredictResultDao:
    """
    模型预测结果数据访问层
    """

    @classmethod
    async def bulk_insert_predictions_dao(cls, db: AsyncSession, records: list[dict[str, Any]]) -> None:
        if not records:
            return
        db_objects = [ModelPredictResult(**record) for record in records]
        db.add_all(db_objects)
        await db.flush()

    @classmethod
    async def get_predict_list(
        cls, db: AsyncSession, query_object: ModelPredictResultPageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        query = (
            select(ModelPredictResult)
            .where(
                ModelPredictResult.result_id == query_object.result_id if query_object.result_id else True,
                ModelPredictResult.ts_code == query_object.ts_code if query_object.ts_code else True,
                ModelPredictResult.trade_date >= query_object.start_date if query_object.start_date else True,
                ModelPredictResult.trade_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(desc(ModelPredictResult.trade_date), ModelPredictResult.ts_code)
            .distinct()
        )

        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        if isinstance(result, PageModel):
            result.rows = CamelCaseUtil.transform_result(result.rows)
        else:
            result = CamelCaseUtil.transform_result(result)
        return result


class ModelSceneBindingDao:
    """
    模型场景绑定数据访问层
    """

    @classmethod
    async def get_active_binding(
        cls, db: AsyncSession, task_id: int, scene_code: str
    ) -> ModelSceneBinding | None:
        return (
            await db.execute(
                select(ModelSceneBinding).where(
                    ModelSceneBinding.task_id == task_id,
                    ModelSceneBinding.scene_code == scene_code,
                    ModelSceneBinding.is_active == '1',
                )
            )
        ).scalars().first()

    @classmethod
    async def deactivate_scene_bindings(cls, db: AsyncSession, task_id: int, scene_code: str) -> int:
        """
        将指定任务+场景下的绑定全部置为非激活状态
        """
        stmt = (
            update(ModelSceneBinding)
            .where(
                ModelSceneBinding.task_id == task_id,
                ModelSceneBinding.scene_code == scene_code,
                ModelSceneBinding.is_active == '1',
            )
            .values(is_active='0', update_time=datetime.now())
        )
        result = await db.execute(stmt)
        return result.rowcount or 0

    @classmethod
    async def upsert_binding(
        cls, db: AsyncSession, task_id: int, scene_code: str, result_id: int
    ) -> ModelSceneBinding:
        """
        为任务+场景绑定指定结果ID，若已存在则更新，否则新增
        """
        # 先将该场景下的旧绑定置为非激活
        await cls.deactivate_scene_bindings(db, task_id, scene_code)

        # 新增一条激活绑定记录
        binding = ModelSceneBinding(
            task_id=task_id,
            scene_code=scene_code,
            result_id=result_id,
            is_active='1',
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        db.add(binding)
        await db.flush()
        await db.refresh(binding)
        return binding

    @classmethod
    async def list_bindings_by_task(cls, db: AsyncSession, task_id: int) -> Sequence[dict[str, Any]]:
        """
        获取某个训练任务下的所有场景绑定记录
        """
        bindings = (
            await db.execute(select(ModelSceneBinding).where(ModelSceneBinding.task_id == task_id))
        ).scalars().all()
        return CamelCaseUtil.transform_result(bindings)


class ModelDataDao:
    """
    模型训练数据准备数据访问层（因子表和价格表关联查询）
    """

    @classmethod
    async def get_training_data(
        cls,
        db: AsyncSession,
        factor_codes: list[str],
        symbol_universe: list[str] | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """
        获取训练数据：关联 feature_data 和 tushare_pro_bar 表

        :param db: orm对象
        :param factor_codes: 因子代码列表
        :param symbol_universe: 股票代码列表（None表示全部）
        :param start_date: 开始日期（YYYYMMDD）
        :param end_date: 结束日期（YYYYMMDD）
        :return: 训练数据列表
        """
        from module_tushare.entity.do.tushare_do import TushareProBar

        # 构建因子值查询（宽表格式）
        factor_query = (
            select(
                FactorValue.trade_date,
                FactorValue.symbol,
                FactorValue.factor_code,
                FactorValue.factor_value,
            )
            .where(
                FactorValue.factor_code.in_(factor_codes),
                FactorValue.trade_date >= start_date,
                FactorValue.trade_date <= end_date,
                FactorValue.symbol.in_(symbol_universe) if symbol_universe else True,
            )
            .order_by(FactorValue.trade_date, FactorValue.symbol, FactorValue.factor_code)
        )

        # 构建价格数据查询
        price_query = (
            select(
                TushareProBar.trade_date,
                TushareProBar.ts_code,
                TushareProBar.open,
                TushareProBar.high,
                TushareProBar.low,
                TushareProBar.close,
                TushareProBar.pre_close,
                TushareProBar.pct_chg,
                TushareProBar.vol,
                TushareProBar.amount,
            )
            .where(
                TushareProBar.trade_date >= start_date,
                TushareProBar.trade_date <= end_date,
                TushareProBar.ts_code.in_(symbol_universe) if symbol_universe else True,
            )
            .order_by(TushareProBar.trade_date, TushareProBar.ts_code)
        )

        # 执行查询
        factor_results = (await db.execute(factor_query)).all()
        price_results = (await db.execute(price_query)).all()

        # 转换为字典格式
        factor_dict: dict[str, dict[str, float]] = {}
        for row in factor_results:
            key = f"{row.trade_date}_{row.symbol}"
            if key not in factor_dict:
                factor_dict[key] = {}
            factor_dict[key][row.factor_code] = float(row.factor_value) if row.factor_value else None

        price_dict: dict[str, dict[str, Any]] = {}
        for row in price_results:
            key = f"{row.trade_date}_{row.ts_code}"
            price_dict[key] = {
                'trade_date': row.trade_date,
                'ts_code': row.ts_code,
                'open': float(row.open) if row.open else None,
                'high': float(row.high) if row.high else None,
                'low': float(row.low) if row.low else None,
                'close': float(row.close) if row.close else None,
                'pre_close': float(row.pre_close) if row.pre_close else None,
                'pct_chg': float(row.pct_chg) if row.pct_chg else None,
                'vol': float(row.vol) if row.vol else None,
                'amount': float(row.amount) if row.amount else None,
            }

        # 合并数据
        training_data = []
        for key in price_dict:
            if key in factor_dict:
                row_data = {**price_dict[key], **factor_dict[key]}
                training_data.append(row_data)

        return training_data

    @classmethod
    async def get_latest_factor_date(
        cls,
        db: AsyncSession,
        factor_codes: list[str],
        symbol_universe: list[str] | None,
    ) -> str | None:
        """
        获取指定因子、指定股票范围内有因子数据的最近一个交易日（YYYYMMDD）。

        :param db: orm 对象
        :param factor_codes: 因子代码列表
        :param symbol_universe: 股票代码列表（None 表示不限制）
        :return: 最近日期字符串，若无数据则返回 None
        """
        stmt = (
            select(func.max(FactorValue.trade_date))
            .where(FactorValue.factor_code.in_(factor_codes))
            .where(FactorValue.symbol.in_(symbol_universe) if symbol_universe else True)
        )
        row = (await db.execute(stmt)).scalars().first()
        if row is None:
            return None
        if hasattr(row, 'strftime'):
            return row.strftime('%Y%m%d')
        return str(row) if row else None

