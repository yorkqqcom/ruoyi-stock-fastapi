import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import CrudResponseModel, PageModel
from module_backtest.dao.backtest_dao import (
    BacktestResultDao,
    BacktestSignalDao,
    BacktestTaskDao,
)
from module_backtest.entity.do.backtest_do import BacktestTask
from module_backtest.entity.vo.backtest_vo import (
    BacktestTaskCreateRequestModel,
    BacktestTaskModel,
    BacktestTaskPageQueryModel,
    BacktestTaskUpdateRequestModel,
    BacktestTradePageQueryModel,
)
from module_backtest.service.backtest_engine import BacktestEngine
from module_factor.dao.factor_dao import ModelTrainResultDao
from utils.log_util import logger


def _has_valid_predict_table_config(result_id: Any, predict_task_id: Any) -> bool:
    """离线模式（predict_table）：需至少指定 result_id 或 predict_task_id。"""
    rid = result_id if (result_id is not None and result_id != '') else None
    if rid is not None:
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            rid = None
    pid = predict_task_id if (predict_task_id is not None and predict_task_id != '') else None
    if pid is not None:
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            pid = None
    return (rid is not None and rid > 0) or (pid is not None and pid > 0)


def _has_valid_online_model_config(result_id: Any, model_scene_binding_id: Any) -> bool:
    """在线模式（online_model）：需至少指定 result_id 或 model_scene_binding_id。"""
    rid = result_id if (result_id is not None and result_id != '') else None
    if rid is not None:
        try:
            rid = int(rid)
        except (TypeError, ValueError):
            rid = None
    mid = model_scene_binding_id if (model_scene_binding_id is not None and model_scene_binding_id != '') else None
    if mid is not None:
        try:
            mid = int(mid)
        except (TypeError, ValueError):
            mid = None
    return (rid is not None and rid > 0) or (mid is not None and mid > 0)


class BacktestService:
    """
    回测业务服务
    """

    @classmethod
    async def create_task_service(
        cls,
        db: AsyncSession,
        request: BacktestTaskCreateRequestModel,
        current_user: str,
    ) -> CrudResponseModel:
        """
        创建回测任务服务

        :param db: orm对象
        :param request: 创建请求
        :param current_user: 当前用户
        :return: 响应结果
        """
        try:
            # 记录服务层入参，进一步排查关键 ID 字段在转换链路中的变化
            # 使用 loguru 的 {} 占位符，确保参数正确输出
            logger.info(
                '[BacktestService] create_task_service 入参: '
                'task_name={} signal_source_type={} result_id={} predict_task_id={} model_scene_binding_id={}',
                request.task_name,
                request.signal_source_type,
                request.result_id,
                request.predict_task_id,
                request.model_scene_binding_id,
            )
            # 1. 参数校验（与执行/更新/引擎内部规则一致）
            #    - predict_table：需配置模型（result_id）或预测任务（predict_task_id）至少其一；
            #    - online_model：需配置模型（result_id）或场景绑定（model_scene_binding_id）至少其一；
            #    - factor_rule：当前暂不支持，通过业务提示限制创建。
            if request.signal_source_type == 'factor_rule':
                return CrudResponseModel(
                    is_success=False,
                    message='当前暂不支持因子规则模式（factor_rule）回测，请选择预测表或在线模型。',
                )
            if request.signal_source_type == 'predict_table':
                if not _has_valid_predict_table_config(request.result_id, request.predict_task_id):
                    return CrudResponseModel(
                        is_success=False,
                        message='离线模式需要指定模型（result_id）或预测任务（predict_task_id）',
                    )
            elif request.signal_source_type == 'online_model':
                if not _has_valid_online_model_config(request.result_id, request.model_scene_binding_id):
                    return CrudResponseModel(
                        is_success=False,
                        message='在线模式需要指定模型（result_id）或场景绑定（model_scene_binding_id）',
                    )

            # 2. 检查信号完整性（离线模式）
            if request.signal_source_type == 'predict_table' and request.result_id:
                # 当 symbol_list 为空时，表示“全部可用个股”，交由 DAO 根据全部信号检查
                symbol_list = (
                    [code.strip() for code in request.symbol_list.split(',') if code.strip()]
                    if request.symbol_list
                    else None
                )
                completeness = await BacktestSignalDao.check_signal_completeness(
                    db, request.result_id, symbol_list, request.start_date, request.end_date
                )
                if not completeness['is_complete']:
                    missing_count = completeness['missing_count']
                    # 当 symbol_list 为空时，missing_count 仅表示“是否存在信号”
                    if symbol_list is None and missing_count > 0:
                        return CrudResponseModel(
                            is_success=False,
                            message='该模型在所选日期范围内没有任何预测结果，请先执行预测任务。',
                        )
                    return CrudResponseModel(
                        is_success=False,
                        message=f'信号数据不完整，缺失 {missing_count} 条信号。请先执行批量预测生成信号。',
                    )

            # 3. 创建任务记录（status=0），严格校验必填字段，避免静默兜底导致误判
            task_name = (request.task_name or '').strip()
            if not task_name:
                return CrudResponseModel(is_success=False, message='任务名称不能为空')

            symbol_list = request.symbol_list if request.symbol_list is not None else ''
            start_date = (request.start_date or '').strip()
            end_date = (request.end_date or '').strip()
            if not start_date or not end_date:
                return CrudResponseModel(is_success=False, message='回测开始日期和结束日期不能为空')

            # 从 request 显式拷贝字段构建 task_model，避免依赖注入/中间件导致 Body 与入库不一致。
            # 这里使用 Pydantic v2 的 model_validate，并通过别名(by_alias=True)传入 camelCase 键，
            # 让 BacktestTaskModel 的 alias_generator=to_camel 正确解析所有字段。
            request_dump_alias = request.model_dump(by_alias=True)
            task_model = BacktestTaskModel.model_validate(request_dump_alias)
            # 服务器侧强制覆盖的字段（避免前端绕过校验）
            task_model.task_name = task_name
            task_model.scene_code = 'backtest'
            task_model.symbol_list = symbol_list
            task_model.start_date = start_date
            task_model.end_date = end_date
            task_model.status = '0'
            task_model.progress = 0
            task_model.create_by = current_user
            # 记录完整的 task_model 内容以及关键字段，方便与 DAO/数据库比对
            logger.info(
                '[BacktestService] BacktestTaskModel dump: {}',
                task_model.model_dump(),
            )
            logger.info(
                '[BacktestService] BacktestTaskModel 核心字段: result_id={} signal_source_type={}',
                task_model.result_id,
                task_model.signal_source_type,
            )

            task_db = await BacktestTaskDao.create_task(
                db, task_model, task_name=task_name, start_date=start_date, end_date=end_date
            )
            task_id = int(task_db.id)
            await db.commit()

            # 新建任务不自动执行，需用户点击「任务运行」按钮触发
            logger.info(f'回测任务已创建（未自动执行），任务ID：{task_id}')
            return CrudResponseModel(
                is_success=True,
                message=f'回测任务已创建，任务ID：{task_id}。请点击任务列表中的「运行」按钮执行回测。',
            )

        except Exception as e:
            logger.error(f'创建回测任务失败：{str(e)}', exc_info=True)
            await db.rollback()
            return CrudResponseModel(is_success=False, message=f'创建回测任务失败：{str(e)}')

    @classmethod
    async def delete_task_service(cls, db: AsyncSession, task_id: int) -> CrudResponseModel:
        """
        删除回测任务（同时删除关联的交易明细、净值、结果）

        :param db: orm对象
        :param task_id: 任务ID
        :return: 响应结果
        """
        task = await BacktestTaskDao.get_task_by_id(db, task_id)
        if not task:
            return CrudResponseModel(is_success=False, message=f'回测任务不存在：{task_id}')
        if task.status == '1':
            return CrudResponseModel(is_success=False, message='任务正在执行中，请先等待执行完成后再删除')
        try:
            deleted = await BacktestTaskDao.delete_task(db, task_id)
            await db.commit()
            if deleted:
                logger.info(f'回测任务已删除，任务ID：{task_id}')
                return CrudResponseModel(is_success=True, message='删除成功')
            return CrudResponseModel(is_success=False, message='删除失败')
        except Exception as e:
            logger.error(f'删除回测任务失败：{str(e)}', exc_info=True)
            await db.rollback()
            return CrudResponseModel(is_success=False, message=f'删除失败：{str(e)}')

    @classmethod
    async def execute_task_service(cls, db: AsyncSession, task_id: int) -> CrudResponseModel:
        """
        执行/重新执行回测任务（仅允许待执行0、失败3）

        :param db: orm对象
        :param task_id: 任务ID
        :return: 响应结果
        """
        task = await BacktestTaskDao.get_task_by_id(db, task_id)
        if not task:
            return CrudResponseModel(is_success=False, message=f'回测任务不存在：{task_id}')
        if task.status == '1':
            return CrudResponseModel(is_success=False, message='任务正在执行中，请勿重复执行')
        if task.status not in ('0', '3'):
            return CrudResponseModel(is_success=False, message='仅支持对待执行或失败任务执行/重新执行')
        # 执行前校验：与创建时规则一致，离线需 result_id 或 predict_task_id，在线需 result_id 或 model_scene_binding_id
        if task.signal_source_type == 'predict_table':
            if not _has_valid_predict_table_config(task.result_id, task.predict_task_id):
                return CrudResponseModel(
                    is_success=False,
                    message='该任务未配置模型或预测任务，无法执行。请删除后重新创建并选择模型。',
                )
        elif task.signal_source_type == 'online_model':
            if not _has_valid_online_model_config(task.result_id, task.model_scene_binding_id):
                return CrudResponseModel(
                    is_success=False,
                    message='该任务未配置模型或场景绑定，无法执行。请删除后重新创建并选择模型。',
                )
        else:
            return CrudResponseModel(
                is_success=False,
                message='当前信号来源类型暂不支持回测，请选择预测表或在线模型。',
            )
        await db.commit()
        # 与数据下载调度一致：通过 APScheduler 提交一次性任务，由调度器线程池执行
        from datetime import datetime

        from apscheduler.triggers.date import DateTrigger

        from config.get_scheduler import scheduler
        from module_backtest.task.backtest_task import run_backtest_job

        job_id = f'backtest_once_{task_id}'
        scheduler.add_job(
            func=run_backtest_job,
            args=(task_id,),
            trigger=DateTrigger(run_date=datetime.now()),
            id=job_id,
            name=f'backtest_once_{task_id}',
            replace_existing=True,
            misfire_grace_time=60,
        )
        logger.info(f'回测任务已提交调度执行，任务ID：{task_id}')
        return CrudResponseModel(is_success=True, message=f'任务已开始执行，任务ID：{task_id}')

    @classmethod
    async def run_backtest_task(cls, db: AsyncSession, task_id: int) -> None:
        """
        执行回测任务（供异步任务调用）

        :param db: orm对象
        :param task_id: 任务ID
        """
        try:
            # 1. 获取任务信息并做执行前校验（避免先置为执行中再失败）
            task = await BacktestTaskDao.get_task_by_id(db, task_id)
            if not task:
                raise ValueError(f'回测任务不存在：{task_id}')
            if task.signal_source_type == 'predict_table':
                if not _has_valid_predict_table_config(task.result_id, task.predict_task_id):
                    raise ValueError(
                        '离线模式需要指定模型（resultId）或预测任务（predictTaskId），当前任务未配置。请删除任务后重新创建并选择模型。'
                    )
            elif task.signal_source_type == 'online_model':
                if not _has_valid_online_model_config(task.result_id, task.model_scene_binding_id):
                    raise ValueError(
                        '在线模式需要指定模型（resultId）或场景绑定（modelSceneBindingId），当前任务未配置。请删除任务后重新创建并选择模型。'
                    )
            else:
                raise ValueError('当前信号来源类型暂不支持回测，请选择预测表（predict_table）或在线模型（online_model）。')

            # 2. 更新任务状态为执行中（status=1）
            await BacktestTaskDao.update_task_status(db, task_id, '1', progress=0)
            await db.commit()

            # 3. 创建BacktestEngine实例
            engine = BacktestEngine(db, task)

            # 4. 加载数据
            logger.info(f'开始加载回测数据，任务ID：{task_id}')
            await engine.load_data()

            # 5. 执行回测
            logger.info(f'开始执行回测，任务ID：{task_id}')
            metrics = await engine.run_backtest()

            # 6. 更新任务状态（成功status=2）
            await BacktestTaskDao.update_task_status(db, task_id, '2', progress=100)
            await db.commit()

            logger.info(f'回测任务执行成功，任务ID：{task_id}，最终净值：{metrics.get("final_equity", 0):.2f}')

        except Exception as e:
            logger.error(f'回测任务执行失败，任务ID：{task_id}，错误：{str(e)}', exc_info=True)
            await db.rollback()
            # 失败状态由 run_async 内用独立新 session 更新，避免已损坏的 db 触发 greenlet 二次异常
            raise

    @classmethod
    async def get_task_page_service(
        cls, db: AsyncSession, query: BacktestTaskPageQueryModel
    ) -> PageModel:
        """
        获取任务分页列表

        :param db: orm对象
        :param query: 查询模型
        :return: 分页结果
        """
        return await BacktestTaskDao.get_task_page(db, query, is_page=True)

    @classmethod
    async def update_task_service(
        cls, db: AsyncSession, task_id: int, request: BacktestTaskUpdateRequestModel
    ) -> CrudResponseModel:
        """
        更新回测任务（仅待执行/失败状态可更新，用于补填模型等）
        """
        task = await BacktestTaskDao.get_task_by_id(db, task_id)
        if not task:
            return CrudResponseModel(is_success=False, message=f'回测任务不存在：{task_id}')
        if task.status not in ('0', '3'):
            return CrudResponseModel(is_success=False, message='仅支持对待执行或失败任务进行编辑')
        # 合并请求与当前任务，得到更新后的有效值用于校验（与创建/执行规则一致）
        effective_signal = request.signal_source_type if request.signal_source_type is not None else task.signal_source_type
        effective_result_id = request.result_id if request.result_id is not None else task.result_id
        effective_predict_task_id = request.predict_task_id if request.predict_task_id is not None else task.predict_task_id
        effective_binding_id = (
            request.model_scene_binding_id if request.model_scene_binding_id is not None else task.model_scene_binding_id
        )
        if effective_signal == 'predict_table':
            if not _has_valid_predict_table_config(effective_result_id, effective_predict_task_id):
                return CrudResponseModel(
                    is_success=False,
                    message='离线模式需要指定模型（resultId）或预测任务（predictTaskId）',
                )
        elif effective_signal == 'online_model':
            if not _has_valid_online_model_config(effective_result_id, effective_binding_id):
                return CrudResponseModel(
                    is_success=False,
                    message='在线模式需要指定模型（resultId）或场景绑定（modelSceneBindingId）',
                )
        elif effective_signal == 'factor_rule':
            return CrudResponseModel(
                is_success=False,
                message='当前暂不支持因子规则模式（factor_rule）回测，请选择预测表或在线模型。',
            )
        updated = await BacktestTaskDao.update_task(db, task_id, request)
        if updated:
            await db.commit()
            return CrudResponseModel(is_success=True, message='任务已更新')
        return CrudResponseModel(is_success=False, message='无有效更新字段')

    @classmethod
    async def get_task_detail_service(cls, db: AsyncSession, task_id: int) -> dict[str, Any]:
        """
        获取任务详情（包含结果摘要）

        :param db: orm对象
        :param task_id: 任务ID
        :return: 任务详情
        """
        task = await BacktestTaskDao.get_task_by_id(db, task_id)
        if not task:
            raise ValueError(f'回测任务不存在：{task_id}')

        # 获取结果摘要
        result = await BacktestResultDao.get_result_by_task_id(db, task_id)

        task_dict = {
            'id': task.id,
            'taskName': task.task_name,
            'status': task.status,
            'progress': task.progress,
            'startDate': task.start_date,
            'endDate': task.end_date,
            'initialCash': float(task.initial_cash) if task.initial_cash else None,
            'createTime': task.create_time,
            'updateTime': task.update_time,
            'signalSourceType': task.signal_source_type,
            'resultId': task.result_id,
            'predictTaskId': task.predict_task_id,
            'modelSceneBindingId': task.model_scene_binding_id,
            'symbolList': task.symbol_list or '',
            'maxPosition': float(task.max_position) if task.max_position is not None else None,
            'commissionRate': float(task.commission_rate) if task.commission_rate is not None else None,
            'slippageBp': task.slippage_bp,
            'signalBuyThreshold': float(task.signal_buy_threshold) if task.signal_buy_threshold is not None else None,
            'signalSellThreshold': float(task.signal_sell_threshold) if task.signal_sell_threshold is not None else None,
            'positionMode': task.position_mode,
            'errorMsg': task.error_msg,
        }

        if result:
            task_dict['result'] = {
                'finalEquity': float(result.final_equity) if result.final_equity else None,
                'totalReturn': float(result.total_return) if result.total_return else None,
                'annualReturn': float(result.annual_return) if result.annual_return else None,
                'maxDrawdown': float(result.max_drawdown) if result.max_drawdown else None,
                'sharpeRatio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
                'tradeCount': result.trade_count,
            }

        return task_dict

    @classmethod
    async def get_result_detail_service(cls, db: AsyncSession, task_id: int) -> dict[str, Any]:
        """
        获取回测结果详情（绩效指标+净值曲线+交易摘要）

        :param db: orm对象
        :param task_id: 任务ID
        :return: 结果详情
        """
        # 获取结果汇总
        result = await BacktestResultDao.get_result_by_task_id(db, task_id)
        if not result:
            raise ValueError(f'回测结果不存在：{task_id}')

        # 获取净值曲线
        nav_list = await BacktestResultDao.get_nav_list(db, task_id)

        # 解析净值曲线JSON
        equity_curve = []
        if result.equity_curve_json:
            import json

            try:
                equity_curve = json.loads(result.equity_curve_json)
            except Exception:
                equity_curve = []

        return {
            'taskId': result.task_id,
            'finalEquity': float(result.final_equity) if result.final_equity else None,
            'totalReturn': float(result.total_return) if result.total_return else None,
            'annualReturn': float(result.annual_return) if result.annual_return else None,
            'maxDrawdown': float(result.max_drawdown) if result.max_drawdown else None,
            'volatility': float(result.volatility) if result.volatility else None,
            'sharpeRatio': float(result.sharpe_ratio) if result.sharpe_ratio else None,
            'calmarRatio': float(result.calmar_ratio) if result.calmar_ratio else None,
            'winRate': float(result.win_rate) if result.win_rate else None,
            'profitLossRatio': float(result.profit_loss_ratio) if result.profit_loss_ratio else None,
            'tradeCount': result.trade_count,
            'equityCurve': equity_curve,
            'navList': nav_list,
            'createTime': result.create_time,
            'updateTime': result.update_time,
        }

    @classmethod
    async def get_trade_page_service(
        cls, db: AsyncSession, query: BacktestTradePageQueryModel
    ) -> PageModel:
        """
        获取交易明细分页列表

        :param db: orm对象
        :param query: 查询模型
        :return: 分页结果
        """
        return await BacktestResultDao.get_trade_page(db, query, is_page=True)
