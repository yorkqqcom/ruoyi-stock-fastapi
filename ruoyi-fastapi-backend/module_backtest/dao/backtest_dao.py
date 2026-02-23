import time
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, delete, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_backtest.entity.do.backtest_do import BacktestNav, BacktestResult, BacktestTask, BacktestTrade
from module_backtest.entity.vo.backtest_vo import (
    BacktestTaskModel,
    BacktestTaskPageQueryModel,
    BacktestTaskUpdateRequestModel,
    BacktestTradePageQueryModel,
)
from module_factor.entity.do.factor_do import ModelPredictResult
from module_tushare.entity.do.tushare_do import TushareProBar
from utils.common_util import CamelCaseUtil
from utils.page_util import PageUtil
from utils.log_util import logger


class BacktestTaskDao:
    """
    回测任务数据访问层
    """

    @classmethod
    async def create_task(
        cls,
        db: AsyncSession,
        task_model: BacktestTaskModel,
        task_name: str,
        start_date: str,
        end_date: str,
    ) -> BacktestTask:
        """创建回测任务。task_name/start_date/end_date 由 Service 校验后显式传入。
        model_scene_binding_id / predict_task_id / result_id 不做任何兜底覆盖，仅使用 task_model 传入值。"""
        row = {
            'task_name': task_name.strip(),
            'scene_code': task_model.scene_code or 'backtest',
            'model_scene_binding_id': task_model.model_scene_binding_id,
            'predict_task_id': task_model.predict_task_id,
            'result_id': task_model.result_id,
            'symbol_list': task_model.symbol_list if task_model.symbol_list is not None else '',
            'start_date': start_date.strip(),
            'end_date': end_date.strip(),
            'initial_cash': task_model.initial_cash,
            'max_position': task_model.max_position,
            'commission_rate': task_model.commission_rate,
            'slippage_bp': task_model.slippage_bp,
            'signal_source_type': task_model.signal_source_type,
            'signal_buy_threshold': task_model.signal_buy_threshold,
            'signal_sell_threshold': task_model.signal_sell_threshold,
            'position_mode': task_model.position_mode,
            'status': task_model.status or '0',
            'progress': task_model.progress if task_model.progress is not None else 0,
            'error_msg': task_model.error_msg,
            'remark': task_model.remark,
            'create_by': task_model.create_by,
            'create_time': task_model.create_time,
            'update_by': task_model.update_by,
            'update_time': task_model.update_time,
        }
        logger.info('[BacktestTaskDao] create_task row: {}', row)
        db_obj = BacktestTask(**row)
        # 强制写入关键字段，避免 ORM/server_default 或会话缓存导致入库为 None/默认值
        db_obj.result_id = task_model.result_id
        db_obj.signal_source_type = task_model.signal_source_type
        db_obj.model_scene_binding_id = task_model.model_scene_binding_id
        db_obj.predict_task_id = task_model.predict_task_id
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
        logger.info(
            '[BacktestTask] create_task 已持久化 id={} result_id={} signal_source_type={}',
            db_obj.id,
            db_obj.result_id,
            db_obj.signal_source_type,
        )
        return db_obj

    @classmethod
    async def get_task_by_id(cls, db: AsyncSession, task_id: int) -> BacktestTask | None:
        """根据ID获取任务"""
        return (await db.execute(select(BacktestTask).where(BacktestTask.id == task_id))).scalars().first()

    @classmethod
    async def update_task_status(
        cls, db: AsyncSession, task_id: int, status: str, progress: int = None, error_msg: str = None
    ) -> None:
        """更新任务状态"""
        update_dict = {'status': status}
        if progress is not None:
            update_dict['progress'] = progress
        if error_msg is not None:
            update_dict['error_msg'] = error_msg
        stmt = update(BacktestTask).where(BacktestTask.id == task_id).values(**update_dict)
        await db.execute(stmt)
        await db.flush()

    @classmethod
    async def update_task(
        cls, db: AsyncSession, task_id: int, update_model: BacktestTaskUpdateRequestModel
    ) -> bool:
        """更新回测任务（仅更新传入的非空字段）"""
        update_dict = {}
        if update_model.task_name is not None:
            update_dict['task_name'] = (update_model.task_name or '').strip() or None
        if update_model.model_scene_binding_id is not None:
            update_dict['model_scene_binding_id'] = update_model.model_scene_binding_id
        if update_model.predict_task_id is not None:
            update_dict['predict_task_id'] = update_model.predict_task_id
        if update_model.result_id is not None:
            update_dict['result_id'] = update_model.result_id
        if update_model.symbol_list is not None:
            update_dict['symbol_list'] = update_model.symbol_list
        if update_model.start_date is not None:
            update_dict['start_date'] = update_model.start_date
        if update_model.end_date is not None:
            update_dict['end_date'] = update_model.end_date
        if update_model.initial_cash is not None:
            update_dict['initial_cash'] = update_model.initial_cash
        if update_model.max_position is not None:
            update_dict['max_position'] = update_model.max_position
        if update_model.commission_rate is not None:
            update_dict['commission_rate'] = update_model.commission_rate
        if update_model.slippage_bp is not None:
            update_dict['slippage_bp'] = update_model.slippage_bp
        if update_model.signal_source_type is not None:
            update_dict['signal_source_type'] = update_model.signal_source_type
        if update_model.signal_buy_threshold is not None:
            update_dict['signal_buy_threshold'] = update_model.signal_buy_threshold
        if update_model.signal_sell_threshold is not None:
            update_dict['signal_sell_threshold'] = update_model.signal_sell_threshold
        if update_model.position_mode is not None:
            update_dict['position_mode'] = update_model.position_mode
        if not update_dict:
            return False
        stmt = update(BacktestTask).where(BacktestTask.id == task_id).values(**update_dict)
        await db.execute(stmt)
        await db.flush()
        return True

    @classmethod
    def _build_task_query(cls, query_object: BacktestTaskPageQueryModel) -> Select[tuple[BacktestTask]]:
        """构建任务查询语句"""
        return (
            select(BacktestTask)
            .where(
                BacktestTask.task_name.like(f'%{query_object.task_name}%') if query_object.task_name else True,
                BacktestTask.status == query_object.status if query_object.status else True,
                BacktestTask.start_date >= query_object.start_date if query_object.start_date else True,
                BacktestTask.end_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(desc(BacktestTask.create_time))
            .distinct()
        )

    @classmethod
    async def get_task_page(
        cls, db: AsyncSession, query_object: BacktestTaskPageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        """分页查询任务列表"""
        query = cls._build_task_query(query_object)
        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        if isinstance(result, PageModel):
            result.rows = CamelCaseUtil.transform_result(result.rows)
        else:
            result = CamelCaseUtil.transform_result(result)
        return result

    @classmethod
    async def delete_task(cls, db: AsyncSession, task_id: int) -> bool:
        """删除回测任务及其关联数据（交易明细、净值、结果、任务）"""
        await db.execute(delete(BacktestTrade).where(BacktestTrade.task_id == task_id))
        await db.execute(delete(BacktestNav).where(BacktestNav.task_id == task_id))
        await db.execute(delete(BacktestResult).where(BacktestResult.task_id == task_id))
        result = await db.execute(delete(BacktestTask).where(BacktestTask.id == task_id))
        await db.flush()
        return result.rowcount > 0


class BacktestKlineDao:
    """
    K线数据访问层
    """

    @classmethod
    async def get_kline_data(
        cls, db: AsyncSession, ts_codes: list[str] | None, start_date: str, end_date: str
    ) -> list[dict[str, Any]]:
        """获取K线数据（从tushare_pro_bar表）"""
        stmt = select(
            TushareProBar.ts_code,
            TushareProBar.trade_date,
            TushareProBar.open,
            TushareProBar.high,
            TushareProBar.low,
            TushareProBar.close,
            TushareProBar.pre_close,
            TushareProBar.vol,
            TushareProBar.amount,
        ).where(
            TushareProBar.trade_date >= start_date,
            TushareProBar.trade_date <= end_date,
        )
        # 当 ts_codes 非空时按股票过滤；为空则表示“全部可用个股”
        if ts_codes:
            stmt = stmt.where(TushareProBar.ts_code.in_(ts_codes))
        stmt = stmt.order_by(TushareProBar.trade_date, TushareProBar.ts_code)
        result = await db.execute(stmt)
        rows = result.mappings().all()
        return [dict(row) for row in rows]


class BacktestSignalDao:
    """
    信号数据访问层
    """

    @classmethod
    async def get_predict_signals(
        cls,
        db: AsyncSession,
        result_id: int,
        ts_codes: list[str] | None,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, Any]]:
        """获取预测信号（从model_predict_result表）"""
        stmt = select(
            ModelPredictResult.ts_code,
            ModelPredictResult.trade_date,
            ModelPredictResult.predict_label,
            ModelPredictResult.predict_prob,
        ).where(
            ModelPredictResult.result_id == result_id,
            ModelPredictResult.trade_date >= start_date,
            ModelPredictResult.trade_date <= end_date,
        )
        # 当 ts_codes 非空时按股票过滤；为空则表示“该模型在日期范围内的所有个股”
        if ts_codes:
            stmt = stmt.where(ModelPredictResult.ts_code.in_(ts_codes))
        stmt = stmt.order_by(ModelPredictResult.trade_date, ModelPredictResult.ts_code)
        result = await db.execute(stmt)
        rows = result.mappings().all()
        return [dict(row) for row in rows]

    @classmethod
    async def check_signal_completeness(
        cls,
        db: AsyncSession,
        result_id: int,
        ts_codes: list[str] | None,
        start_date: str,
        end_date: str,
    ) -> dict[str, Any]:
        """检查信号完整性（返回缺失日期列表）"""
        # 如果未指定 ts_codes，则只检查在日期范围内是否存在任何信号
        if not ts_codes:
            stmt = select(func.count()).select_from(ModelPredictResult).where(
                ModelPredictResult.result_id == result_id,
                ModelPredictResult.trade_date >= start_date,
                ModelPredictResult.trade_date <= end_date,
            )
            total = (await db.execute(stmt)).scalar() or 0
            return {
                'is_complete': total > 0,
                'missing_count': 0 if total > 0 else 1,
                'missing_signals': [],
            }

        # 获取所有交易日期（限定在给定标的和日期范围内）
        kline_dates_stmt = (
            select(TushareProBar.trade_date)
            .where(
                TushareProBar.ts_code.in_(ts_codes),
                TushareProBar.trade_date >= start_date,
                TushareProBar.trade_date <= end_date,
            )
            .distinct()
            .order_by(TushareProBar.trade_date)
        )
        kline_dates_result = await db.execute(kline_dates_stmt)
        kline_dates = {row[0] for row in kline_dates_result.all()}

        # 获取已有信号的日期
        signal_dates_stmt = (
            select(ModelPredictResult.trade_date, ModelPredictResult.ts_code)
            .where(
                ModelPredictResult.result_id == result_id,
                ModelPredictResult.ts_code.in_(ts_codes),
                ModelPredictResult.trade_date >= start_date,
                ModelPredictResult.trade_date <= end_date,
            )
            .distinct()
        )
        signal_dates_result = await db.execute(signal_dates_stmt)
        signal_dates_set = {(row[0], row[1]) for row in signal_dates_result.all()}

        # 计算缺失的信号
        missing_signals = []
        for ts_code in ts_codes:
            for date in kline_dates:
                if (date, ts_code) not in signal_dates_set:
                    missing_signals.append({'ts_code': ts_code, 'trade_date': date})

        return {
            'is_complete': len(missing_signals) == 0,
            'missing_count': len(missing_signals),
            'missing_signals': missing_signals[:100],  # 最多返回100条
        }

    @classmethod
    async def list_ts_codes_from_predict(
        cls, db: AsyncSession, result_id: int, start_date: str, end_date: str
    ) -> list[str]:
        """从预测结果中推导标的列表（按 resultId + 日期范围）"""
        stmt = (
            select(ModelPredictResult.ts_code)
            .where(
                ModelPredictResult.result_id == result_id,
                ModelPredictResult.trade_date >= start_date,
                ModelPredictResult.trade_date <= end_date,
            )
            .distinct()
            .order_by(ModelPredictResult.ts_code)
        )
        rows = (await db.execute(stmt)).scalars().all()
        return list(rows)


class BacktestResultDao:
    """
    回测结果数据访问层
    """

    @classmethod
    async def save_result(cls, db: AsyncSession, task_id: int, metrics: dict[str, Any]) -> BacktestResult:
        """保存回测结果汇总"""
        # 检查是否已存在结果
        existing = (
            await db.execute(select(BacktestResult).where(BacktestResult.task_id == task_id))
        ).scalars().first()

        if existing:
            # 更新现有结果
            for key, value in metrics.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            await db.flush()
            await db.refresh(existing)
            return existing
        else:
            # 创建新结果
            result_dict = {'task_id': task_id, **metrics}
            db_obj = BacktestResult(**result_dict)
            db.add(db_obj)
            await db.flush()
            await db.refresh(db_obj)
            return db_obj

    @classmethod
    async def bulk_insert_trades(cls, db: AsyncSession, trades: list[dict[str, Any]]) -> None:
        """批量插入交易明细"""
        if not trades:
            return
        db_objects = [BacktestTrade(**trade) for trade in trades]
        db.add_all(db_objects)
        await db.flush()

    @classmethod
    async def bulk_insert_navs(cls, db: AsyncSession, navs: list[dict[str, Any]]) -> None:
        """批量插入净值日频数据"""
        if not navs:
            return
        db_objects = [BacktestNav(**nav) for nav in navs]
        db.add_all(db_objects)
        await db.flush()

    @classmethod
    async def get_result_by_task_id(cls, db: AsyncSession, task_id: int) -> BacktestResult | None:
        """根据任务ID获取结果"""
        return (
            await db.execute(select(BacktestResult).where(BacktestResult.task_id == task_id))
        ).scalars().first()

    @classmethod
    async def get_trade_page(
        cls, db: AsyncSession, query_object: BacktestTradePageQueryModel, is_page: bool = True
    ) -> PageModel | list[dict[str, Any]]:
        """分页查询交易明细"""
        query = (
            select(BacktestTrade)
            .where(
                BacktestTrade.task_id == query_object.task_id,
                BacktestTrade.ts_code == query_object.ts_code if query_object.ts_code else True,
                BacktestTrade.trade_date >= query_object.start_date if query_object.start_date else True,
                BacktestTrade.trade_date <= query_object.end_date if query_object.end_date else True,
            )
            .order_by(desc(BacktestTrade.trade_date), BacktestTrade.ts_code)
        )

        result: PageModel | list[dict[str, Any]] = await PageUtil.paginate(
            db, query, query_object.page_num, query_object.page_size, is_page
        )
        if isinstance(result, PageModel):
            result.rows = CamelCaseUtil.transform_result(result.rows)
        else:
            result = CamelCaseUtil.transform_result(result)
        return result

    @classmethod
    async def get_nav_list(cls, db: AsyncSession, task_id: int) -> list[dict[str, Any]]:
        """获取净值列表"""
        stmt = (
            select(BacktestNav)
            .where(BacktestNav.task_id == task_id)
            .order_by(BacktestNav.trade_date)
        )
        result = await db.execute(stmt)
        navs = result.scalars().all()
        return CamelCaseUtil.transform_result(navs)
