from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from common.vo import PageModel
from module_backtest.entity.do.backtest_do import BacktestNav, BacktestResult, BacktestTask, BacktestTrade
from module_backtest.entity.vo.backtest_vo import (
    BacktestTaskModel,
    BacktestTaskPageQueryModel,
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
    async def create_task(cls, db: AsyncSession, task_model: BacktestTaskModel) -> BacktestTask:
        """创建回测任务"""
        db_obj = BacktestTask(**task_model.model_dump(exclude={'id'}))
        db.add(db_obj)
        await db.flush()
        await db.refresh(db_obj)
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
