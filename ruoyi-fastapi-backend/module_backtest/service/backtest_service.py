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
    BacktestTradePageQueryModel,
)
from module_backtest.service.backtest_engine import BacktestEngine
from module_factor.dao.factor_dao import ModelTrainResultDao
from config.database import AsyncSessionLocal
from utils.log_util import logger


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
            # 1. 参数校验
            if request.signal_source_type == 'predict_table':
                if not request.result_id and not request.predict_task_id:
                    return CrudResponseModel(
                        is_success=False, message='离线模式需要指定result_id或predict_task_id'
                    )
            elif request.signal_source_type == 'online_model':
                if not request.result_id:
                    return CrudResponseModel(is_success=False, message='在线模式需要指定result_id')

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

            # 3. 创建任务记录（status=0）
            task_model = BacktestTaskModel(
                task_name=request.task_name,
                scene_code='backtest',
                model_scene_binding_id=request.model_scene_binding_id,
                predict_task_id=request.predict_task_id,
                result_id=request.result_id,
                symbol_list=request.symbol_list,
                start_date=request.start_date,
                end_date=request.end_date,
                initial_cash=request.initial_cash,
                max_position=request.max_position,
                commission_rate=request.commission_rate,
                slippage_bp=request.slippage_bp,
                signal_source_type=request.signal_source_type,
                signal_buy_threshold=request.signal_buy_threshold,
                signal_sell_threshold=request.signal_sell_threshold,
                position_mode=request.position_mode,
                status='0',
                progress=0,
                create_by=current_user,
            )

            task_db = await BacktestTaskDao.create_task(db, task_model)
            task_id = int(task_db.id)
            await db.commit()

            # 4. 启动异步任务（延迟导入以避免循环依赖）
            from module_backtest.task.backtest_task import execute_backtest_task

            execute_backtest_task(AsyncSessionLocal, task_id)

            logger.info(f'回测任务已创建并启动，任务ID：{task_id}')
            return CrudResponseModel(is_success=True, message=f'回测任务已创建并启动，任务ID：{task_id}')

        except Exception as e:
            logger.error(f'创建回测任务失败：{str(e)}', exc_info=True)
            await db.rollback()
            return CrudResponseModel(is_success=False, message=f'创建回测任务失败：{str(e)}')

    @classmethod
    async def run_backtest_task(cls, db: AsyncSession, task_id: int) -> None:
        """
        执行回测任务（供异步任务调用）

        :param db: orm对象
        :param task_id: 任务ID
        """
        try:
            # 1. 更新任务状态为执行中（status=1）
            await BacktestTaskDao.update_task_status(db, task_id, '1', progress=0)
            await db.commit()

            # 2. 获取任务信息
            task = await BacktestTaskDao.get_task_by_id(db, task_id)
            if not task:
                raise ValueError(f'回测任务不存在：{task_id}')

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
            # 更新任务状态（失败status=3）
            try:
                await BacktestTaskDao.update_task_status(db, task_id, '3', error_msg=str(e))
                await db.commit()
            except Exception as commit_error:
                logger.error(f'更新任务状态失败：{str(commit_error)}')

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
