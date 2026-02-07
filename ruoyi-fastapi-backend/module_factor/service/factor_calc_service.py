from datetime import datetime, timedelta
import json
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from module_factor.dao.factor_dao import FactorCalcLogDao, FactorValueDao
from module_factor.entity.do.factor_do import FactorCalcLog, FactorDefinition, FactorTask
from utils.log_util import logger


class FactorCalcService:
    """
    因子计算引擎（首版实现）

    限制与约定（后续可以逐步增强）：
    - 仅支持 `calc_type = PY_EXPR` 的因子；
    - `source_table` 必须是已存在的行情表名（如通过 Tushare 下载创建的表），且包含：
      - 日期列：`trade_date`（YYYYMMDD）
      - 代码列：默认 `ts_code`，可在因子 `params` JSON 中通过 `{"symbol_col":"ts_code"}` 覆盖；
    - `expr` 为基于 pandas 的表达式，返回 `pd.Series`，索引与行情 DataFrame 对齐；
    - 结果写入 `feature_data` 表。
    """

    @classmethod
    async def _get_next_trade_date(
        cls,
        db: AsyncSession,
        table_name: str,
        from_date: datetime,
        max_days: int = 10,
    ) -> str | None:
        """
        从行情表中查找下一个交易日

        :param db: 数据库会话
        :param table_name: 行情表名
        :param from_date: 起始日期（datetime对象）
        :param max_days: 最多查找天数
        :return: 下一个交易日（YYYYMMDD格式），如果未找到则返回None
        """
        try:
            # 将datetime转换为YYYYMMDD格式
            from_date_str = from_date.strftime('%Y%m%d')
            # 计算最大查找日期
            max_date = (from_date + timedelta(days=max_days)).strftime('%Y%m%d')

            sql = f"""
                SELECT DISTINCT trade_date 
                FROM {table_name} 
                WHERE trade_date > :from_date AND trade_date <= :max_date
                ORDER BY trade_date ASC 
                LIMIT 1
            """
            result = await db.execute(text(sql), {'from_date': from_date_str, 'max_date': max_date})
            row = result.first()
            if row:
                return str(row[0])
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning('查找下一个交易日失败: %s', exc)
            return None

    @classmethod
    async def _get_latest_trade_date(
        cls,
        db: AsyncSession,
        table_name: str,
    ) -> str | None:
        """
        从行情表中查找最新的交易日

        :param db: 数据库会话
        :param table_name: 行情表名
        :return: 最新交易日（YYYYMMDD格式），如果未找到则返回None
        """
        try:
            sql = f"""
                SELECT MAX(trade_date) as max_date
                FROM {table_name}
            """
            result = await db.execute(text(sql))
            row = result.first()
            if row and row[0]:
                return str(row[0])
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning('查找最新交易日失败: %s', exc)
            return None

    @classmethod
    async def _get_earliest_trade_date(
        cls,
        db: AsyncSession,
        table_name: str,
    ) -> str | None:
        """
        从行情表中查找最早的交易日

        :param db: 数据库会话
        :param table_name: 行情表名
        :return: 最早交易日（YYYYMMDD格式），如果未找到则返回None
        """
        try:
            sql = f"""
                SELECT MIN(trade_date) as min_date
                FROM {table_name}
            """
            result = await db.execute(text(sql))
            row = result.first()
            if row and row[0]:
                return str(row[0])
            return None
        except Exception as exc:  # noqa: BLE001
            logger.warning('查找最早交易日失败: %s', exc)
            return None

    @classmethod
    async def _adjust_date_range_for_increment(
        cls,
        db: AsyncSession,
        task: FactorTask,
        factor_defs: list[FactorDefinition],
        original_start_date: str,
        original_end_date: str,
    ) -> tuple[str | None, str | None]:
        """
        根据增量模式调整日期范围

        :param db: 数据库会话
        :param task: 任务对象
        :param factor_defs: 因子定义列表
        :param original_start_date: 原始开始日期（可为空）
        :param original_end_date: 原始结束日期（可为空）
        :return: (调整后的开始日期, 调整后的结束日期)，可能为None
        """
        task_run_mode = getattr(task, 'run_mode', 'increment') or 'increment'
        task_last_run_time = getattr(task, 'last_run_time', None)

        # 如果不是增量模式，直接返回原始日期范围
        if task_run_mode != 'increment':
            logger.info(
                '任务运行模式为 %s，使用原始日期范围: %s~%s',
                task_run_mode,
                original_start_date or '空',
                original_end_date or '空',
            )
            return original_start_date or None, original_end_date or None

        # 需要从第一个因子的source_table中查找交易日
        # 如果多个因子使用不同的表，使用第一个因子的表
        if not factor_defs or not factor_defs[0].source_table:
            logger.warning('无法确定行情表，使用原始日期范围')
            return original_start_date or None, original_end_date or None

        source_table = factor_defs[0].source_table

        # 查找最新交易日（用于确定结束日期）
        latest_trade_date = await cls._get_latest_trade_date(db, source_table)
        if not latest_trade_date:
            logger.warning('未找到最新交易日，无法确定结束日期')
            # 如果没有最新交易日，且原始结束日期也为空，返回None
            if not original_end_date:
                return original_start_date or None, None

        # 增量模式：根据是否有上次运行时间来决定开始日期
        if task_last_run_time:
            # 有上次运行时间：从上次运行时间的下一个交易日开始
            next_trade_date = await cls._get_next_trade_date(db, source_table, task_last_run_time)
            if not next_trade_date:
                logger.warning(
                    '未找到下一个交易日（从 %s 开始）',
                    task_last_run_time.strftime('%Y%m%d'),
                )
                # 如果找不到下一个交易日，且原始开始日期为空，尝试使用最早交易日
                if not original_start_date:
                    earliest_trade_date = await cls._get_earliest_trade_date(db, source_table)
                    if earliest_trade_date:
                        adjusted_start = earliest_trade_date
                        logger.info('使用最早交易日作为开始日期: %s', adjusted_start)
                    else:
                        adjusted_start = None
                else:
                    adjusted_start = original_start_date
            else:
                # 找到了下一个交易日
                if original_start_date:
                    # 如果原始开始日期存在，取两者中的较大值（更晚的日期）
                    adjusted_start = max(next_trade_date, original_start_date)
                else:
                    # 如果原始开始日期为空，使用下一个交易日
                    adjusted_start = next_trade_date
        else:
            # 没有上次运行时间（首次运行）
            if original_start_date:
                adjusted_start = original_start_date
            else:
                # 原始开始日期也为空，使用最早交易日
                earliest_trade_date = await cls._get_earliest_trade_date(db, source_table)
                if earliest_trade_date:
                    adjusted_start = earliest_trade_date
                    logger.info('首次运行且无开始日期，使用最早交易日: %s', adjusted_start)
                else:
                    adjusted_start = None

        # 确定结束日期
        if original_end_date:
            # 如果原始结束日期存在，取最新交易日和原始结束日期中的较小值（更早的日期）
            if latest_trade_date:
                adjusted_end = min(latest_trade_date, original_end_date)
            else:
                adjusted_end = original_end_date
        else:
            # 如果原始结束日期为空，使用最新交易日
            adjusted_end = latest_trade_date

        # 验证日期范围
        if adjusted_start and adjusted_end and adjusted_start > adjusted_end:
            logger.info(
                '调整后的日期范围无效（%s > %s），可能没有新数据需要计算',
                adjusted_start,
                adjusted_end,
            )
            return adjusted_start, adjusted_end

        logger.info(
            '增量模式：开始日期=%s，结束日期=%s（原始: %s~%s，上次运行: %s）',
            adjusted_start or '空',
            adjusted_end or '空',
            original_start_date or '空',
            original_end_date or '空',
            task_last_run_time.strftime('%Y-%m-%d %H:%M:%S') if task_last_run_time else '无',
        )

        return adjusted_start, adjusted_end

    @classmethod
    async def calc_task(
        cls,
        db: AsyncSession,
        task: FactorTask,
        factor_defs: list[FactorDefinition],
    ) -> None:
        """
        按任务配置计算一批因子
        """
        start_time = datetime.now()
        # 提前缓存任务关键字段，避免在异步上下文中触发 ORM 懒加载（MissingGreenlet）
        task_id = getattr(task, 'id', None)
        task_name = getattr(task, 'task_name', None) or (f'task_{task_id}' if task_id is not None else 'task_unknown')
        task_factor_codes = getattr(task, 'factor_codes', '') or ''
        task_symbol_universe = getattr(task, 'symbol_universe', '') or ''
        task_start_date = getattr(task, 'start_date', '') or ''
        task_end_date = getattr(task, 'end_date', '') or ''
        
        # 根据增量模式调整日期范围
        actual_start_date, actual_end_date = await cls._adjust_date_range_for_increment(
            db=db,
            task=task,
            factor_defs=factor_defs,
            original_start_date=task_start_date,
            original_end_date=task_end_date,
        )

        logger.info(
            '开始执行因子任务计算: %s(ID=%s), 因子=%s, 原始日期区间=%s~%s, 实际计算区间=%s~%s',
            task_name,
            task_id,
            [d.factor_code for d in factor_defs],
            task_start_date,
            task_end_date,
            actual_start_date,
            actual_end_date,
        )

        # 检查日期范围是否有效
        # 如果两个日期都为空，无法执行
        if not actual_start_date and not actual_end_date:
            logger.warning('因子任务 %s(ID=%s) 调整后的日期范围为空，无法执行', task_name, task_id)
            return

        # 如果只有一个日期为空，尝试从行情表中获取
        if not actual_start_date or not actual_end_date:
            if not factor_defs or not factor_defs[0].source_table:
                logger.warning('因子任务 %s(ID=%s) 日期范围不完整且无法确定行情表，暂不执行', task_name, task_id)
                return
            
            source_table = factor_defs[0].source_table
            
            if not actual_start_date:
                # 开始日期为空，使用最早交易日
                actual_start_date = await cls._get_earliest_trade_date(db, source_table)
                if not actual_start_date:
                    logger.warning('因子任务 %s(ID=%s) 无法确定开始日期，暂不执行', task_name, task_id)
                    return
                logger.info('使用最早交易日作为开始日期: %s', actual_start_date)
            
            if not actual_end_date:
                # 结束日期为空，使用最新交易日
                actual_end_date = await cls._get_latest_trade_date(db, source_table)
                if not actual_end_date:
                    logger.warning('因子任务 %s(ID=%s) 无法确定结束日期，暂不执行', task_name, task_id)
                    return
                logger.info('使用最新交易日作为结束日期: %s', actual_end_date)

        # 检查调整后的日期范围是否有效
        if actual_start_date > actual_end_date:
            logger.info(
                '因子任务 %s(ID=%s) 调整后的日期范围无效（%s > %s），可能没有新数据需要计算，跳过执行',
                task_name,
                task_id,
                actual_start_date,
                actual_end_date,
            )
            return

        # 解析标的范围：当前仅支持 type=list 且 symbols 字段
        symbols: list[str] | None = None
        if task_symbol_universe:
            try:
                uni = json.loads(task_symbol_universe)
                if isinstance(uni, dict) and uni.get('type') == 'list':
                    symbols = uni.get('symbols') or uni.get('tsCodes') or []
                    if not isinstance(symbols, list):
                        symbols = None
                # 其他类型（all/index 等）暂不处理，视为全市场
            except Exception as exc:  # noqa: BLE001
                logger.warning('解析 symbol_universe 失败: %s, 内容=%s', exc, task.symbol_universe)

        total_records = 0
        error_messages = []

        try:
            for definition in factor_defs:
                if definition.calc_type != 'PY_EXPR':
                    logger.info(
                        '因子 %s(calc_type=%s) 当前仅支持 PY_EXPR，跳过',
                        definition.factor_code,
                        definition.calc_type,
                    )
                    continue

                if not definition.source_table:
                    logger.warning('因子 %s 未配置 source_table，跳过', definition.factor_code)
                    continue

                try:
                    records = await cls._calc_single_factor_py_expr(
                        db=db,
                        task=task,
                        definition=definition,
                        symbols=symbols,
                        start_date=actual_start_date,
                        end_date=actual_end_date,
                    )
                    total_records += records
                except Exception as factor_exc:  # noqa: BLE001
                    error_msg = f'因子 {definition.factor_code} 计算失败: {str(factor_exc)}'
                    logger.exception(error_msg)
                    error_messages.append(error_msg)
                    # 继续计算其他因子，不中断整个任务

            duration = int((datetime.now() - start_time).total_seconds())
            status = '0' if not error_messages else '1'
            error_message = '; '.join(error_messages) if error_messages else None
            if error_message and len(error_message) > 2000:
                error_message = error_message[:2000] + '...'

            # 为避免日志写入失败导致整个事务回滚，这里单独加一层保护
            try:
                log = FactorCalcLog(
                    task_id=task_id or 0,
                    task_name=task_name,
                    factor_codes=task_factor_codes,
                    symbol_universe=task_symbol_universe,
                    start_date=actual_start_date,
                    end_date=actual_end_date,
                    status=status,
                    record_count=total_records,
                    duration=duration,
                    error_message=error_message,
                    create_time=datetime.now(),
                )
                await FactorCalcLogDao.add_log_dao(db, log)
            except Exception as exc:  # noqa: BLE001
                # 记录错误，但不影响前面 feature_data 插入的提交
                logger.exception('写入因子计算日志失败: %s', exc)

            # 无论日志是否写成功，都提交前面因子结果插入
            await db.commit()

            if status == '0':
                logger.info(
                    '因子任务 %s(ID=%s) 计算完成，总记录数=%s，耗时=%s秒',
                    task_name,
                    task_id,
                    total_records,
                    duration,
                )
            else:
                logger.warning(
                    '因子任务 %s(ID=%s) 计算部分失败，总记录数=%s，耗时=%s秒，错误=%s',
                    task_name,
                    task_id,
                    total_records,
                    duration,
                    error_message,
                )
        except Exception as exc:  # noqa: BLE001
            # 捕获整个计算过程的异常，重新抛出给上层处理
            duration = int((datetime.now() - start_time).total_seconds())
            logger.exception('因子任务 %s(ID=%s) 计算过程发生异常', task_name, task_id)
            # 尝试记录错误日志
            try:
                error_msg = str(exc)[:2000]
                log = FactorCalcLog(
                    task_id=task_id or 0,
                    task_name=task_name,
                    factor_codes=task_factor_codes,
                    symbol_universe=task_symbol_universe,
                    start_date=actual_start_date,
                    end_date=actual_end_date,
                    status='1',
                    record_count=total_records,
                    duration=duration,
                    error_message=error_msg,
                    create_time=datetime.now(),
                )
                await FactorCalcLogDao.add_log_dao(db, log)
                await db.commit()
            except Exception as log_exc:  # noqa: BLE001
                logger.exception('写入因子计算错误日志失败: %s', log_exc)
            # 重新抛出异常，让上层处理
            raise

    @classmethod
    async def _load_price_data(
        cls,
        db: AsyncSession,
        table_name: str,
        start_date: str,
        end_date: str,
        symbols: list[str] | None,
        symbol_col: str,
    ) -> pd.DataFrame:
        """
        从动态行情表加载数据为 DataFrame
        """
        # 基本字段：日期 + 代码 + 其他所有列
        where_clauses = ['trade_date >= :start_date', 'trade_date <= :end_date']
        params: dict[str, Any] = {'start_date': start_date, 'end_date': end_date}
        if symbols:
            where_clauses.append(f'{symbol_col} IN :symbols')
            params['symbols'] = tuple(symbols)

        where_sql = ' AND '.join(where_clauses)
        sql = f'SELECT * FROM {table_name} WHERE {where_sql} ORDER BY trade_date, {symbol_col}'
        logger.debug('加载行情 SQL: %s, params=%s', sql, params)

        result = await db.execute(text(sql), params)
        rows = result.mappings().all()
        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        return df

    @classmethod
    async def _calc_single_factor_py_expr(
        cls,
        db: AsyncSession,
        task: FactorTask,
        definition: FactorDefinition,
        symbols: list[str] | None,
        start_date: str,
        end_date: str,
    ) -> int:
        """
        基于 pandas 表达式的单个因子计算
        """
        factor_code = definition.factor_code
        table_name = definition.source_table
        if not factor_code or not table_name:
            return 0

        # 解析参数：目前仅支持 symbol_col
        symbol_col = 'ts_code'
        if definition.params:
            try:
                params = json.loads(definition.params)
                if isinstance(params, dict) and params.get('symbol_col'):
                    symbol_col = params['symbol_col']
            except Exception as exc:  # noqa: BLE001
                logger.warning('解析因子 %s params 失败: %s', factor_code, exc)

        df = await cls._load_price_data(
            db=db,
            table_name=table_name,
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            symbol_col=symbol_col,
        )
        if df.empty:
            logger.warning(
                '因子 %s 在表 %s 上区间 %s~%s 未加载到任何行情数据',
                factor_code,
                table_name,
                start_date,
                end_date,
            )
            return 0

        if not definition.expr:
            logger.warning('因子 %s 未配置 expr 表达式，跳过', factor_code)
            return 0

        # 执行表达式
        try:
            local_env: dict[str, Any] = {'df': df, 'pd': pd, 'np': np}
            # expr 示例：(df["close"] / df["close"].shift(1) - 1).rolling(window=5).mean()
            series = eval(definition.expr, {"__builtins__": {}}, local_env)  # noqa: S307
            if not isinstance(series, pd.Series):
                logger.warning('因子 %s 表达式结果不是 Series 类型，实际为 %s', factor_code, type(series))
                return 0
        except Exception as exc:  # noqa: BLE001
            logger.exception('执行因子 %s 表达式失败: %s, expr=%s', factor_code, exc, definition.expr)
            return 0

        # 对齐索引，过滤缺失值
        series = series.reindex(df.index)
        mask = ~series.isna()
        if not mask.any():
            logger.warning('因子 %s 计算结果全部为空，跳过写入', factor_code)
            return 0

        valid_df = df.loc[mask].copy()
        valid_series = series[mask]

        # 组装写入因子结果表的数据
        now = datetime.now()
        records: list[dict[str, Any]] = []
        for idx, row in valid_df.iterrows():
            trade_date = str(row.get('trade_date') or '')
            symbol = str(row.get(symbol_col) or '')
            if not trade_date or not symbol:
                continue
            value = valid_series.loc[idx]
            # 把 numpy 类型转为 Python 基本类型
            if isinstance(value, (np.generic,)):
                value = value.item()
            records.append(
                {
                    'trade_date': trade_date,
                    'symbol': symbol,
                    'factor_code': factor_code,
                    'factor_value': value,
                    'task_id': task.id,
                    'calc_date': now,
                    'extra': None,
                }
            )

        if not records:
            logger.warning('因子 %s 有效记录数为 0，跳过写入', factor_code)
            return 0

        await FactorValueDao.bulk_insert_values_dao(db, records)
        logger.info(
            '因子 %s 写入 feature_data 记录数: %s (表=%s, 区间=%s~%s)',
            factor_code,
            len(records),
            table_name,
            start_date,
            end_date,
        )
        return len(records)


