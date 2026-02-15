import json
from collections import defaultdict
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from module_backtest.dao.backtest_dao import BacktestKlineDao, BacktestSignalDao
from module_backtest.entity.do.backtest_do import BacktestTask
from module_factor.dao.factor_dao import ModelDataDao, ModelTrainResultDao
from utils.log_util import logger

try:
    import joblib
except ImportError:
    joblib = None


class BacktestEngine:
    """
    回测引擎核心类
    """

    def __init__(self, db: AsyncSession, task: BacktestTask):
        self.db = db
        self.task = task
        self.cash = float(task.initial_cash)
        self.positions = {}  # {ts_code: shares}
        self.trades = []
        self.navs = []
        self.kline_data = None
        self.signal_data = None
        self.model = None  # 用于在线模式

    async def load_data(self) -> None:
        """加载K线和信号数据"""
        # 解析标的列表（允许为空：为空时按不同模式自动推导标的集合）
        symbol_list_str = (self.task.symbol_list or '').strip()
        ts_codes: list[str] | None = [code.strip() for code in symbol_list_str.split(',') if code.strip()] or None

        # 如果未指定标的且为离线模式，从预测结果中推导标的列表
        if ts_codes is None and self.task.signal_source_type == 'predict_table':
            if not self.task.result_id:
                raise ValueError('离线模式需要指定result_id')
            logger.info(
                f'标的列表为空，将从预测结果中推导标的集合：result_id={self.task.result_id}, '
                f'date_range={self.task.start_date}~{self.task.end_date}'
            )
            ts_codes = await BacktestSignalDao.list_ts_codes_from_predict(
                self.db, self.task.result_id, self.task.start_date, self.task.end_date
            )
            if not ts_codes:
                raise ValueError('该模型在指定日期范围内没有任何预测结果，无法回测')

        # 1. 加载K线数据（ts_codes 为空表示“全部可用个股”）
        logger.info(
            f'加载K线数据：{"全部个股" if not ts_codes else str(len(ts_codes)) + "个标的"}，'
            f'日期范围：{self.task.start_date} ~ {self.task.end_date}'
        )
        kline_list = await BacktestKlineDao.get_kline_data(
            self.db, ts_codes, self.task.start_date, self.task.end_date
        )
        if not kline_list:
            raise ValueError('未找到K线数据')

        self.kline_data = pd.DataFrame(kline_list)
        logger.info(f'K线数据加载完成，共 {len(self.kline_data)} 条记录')

        # 2. 根据signal_source_type加载或生成信号
        if self.task.signal_source_type == 'predict_table':
            # 离线模式：从model_predict_result查询
            if not self.task.result_id:
                raise ValueError('离线模式需要指定result_id')

            logger.info(f'加载预测信号：result_id={self.task.result_id}')
            signal_list = await BacktestSignalDao.get_predict_signals(
                self.db, self.task.result_id, ts_codes, self.task.start_date, self.task.end_date
            )
            if not signal_list:
                raise ValueError('未找到预测信号数据')

            self.signal_data = pd.DataFrame(signal_list)
            logger.info(f'预测信号加载完成，共 {len(self.signal_data)} 条记录')

        elif self.task.signal_source_type == 'online_model':
            # 在线模式：动态调用模型
            if not self.task.result_id:
                raise ValueError('在线模式需要指定result_id')

            logger.info(f'在线模式：加载模型 result_id={self.task.result_id}')
            result = await ModelTrainResultDao.get_result_by_id(self.db, self.task.result_id)
            if not result:
                raise ValueError('训练结果不存在')

            if not result.model_file_path or not result.feature_importance:
                raise ValueError('模型文件或特征重要性不存在')

            if joblib is None:
                raise ImportError('joblib未安装，无法使用在线模式')

            self.model = joblib.load(result.model_file_path)
            feature_importance = json.loads(result.feature_importance)
            self.feature_cols = list(feature_importance.keys())
            logger.info(f'模型加载完成，特征数量：{len(self.feature_cols)}')

            # 在线模式的信号数据将在回测循环中动态生成
            self.signal_data = None
        else:
            raise ValueError(f'不支持的信号来源类型：{self.task.signal_source_type}')

    async def run_backtest(self) -> dict[str, Any]:
        """执行回测主循环"""
        # 1. 获取交易日列表（从K线数据中提取唯一日期，排序）
        trade_dates = sorted(self.kline_data['trade_date'].unique())

        if not trade_dates:
            raise ValueError('未找到交易日数据')

        logger.info(f'开始回测，交易日数量：{len(trade_dates)}')

        # 2. 初始化状态
        self.cash = float(self.task.initial_cash)
        self.positions = {}
        self.trades = []
        self.navs = []

        # 3. 按日期循环
        total_dates = len(trade_dates)
        for idx, date in enumerate(trade_dates):
            try:
                # 3.1 获取当日K线数据（按ts_code分组）
                daily_kline = self.kline_data[self.kline_data['trade_date'] == date].copy()

                # 3.2 获取当日信号
                if self.task.signal_source_type == 'predict_table':
                    # 从已加载的信号数据中获取
                    daily_signals_df = self.signal_data[self.signal_data['trade_date'] == date]
                    daily_signals = {}
                    for _, row in daily_signals_df.iterrows():
                        daily_signals[row['ts_code']] = {
                            'predict_label': row.get('predict_label'),
                            'predict_prob': float(row.get('predict_prob', 0)),
                        }
                elif self.task.signal_source_type == 'online_model':
                    # 动态生成信号
                    daily_signals = await self._generate_online_signals(date, daily_kline['ts_code'].tolist())
                else:
                    daily_signals = {}

                # 3.3 计算目标仓位
                target_positions = self._generate_target_position(date, daily_signals, daily_kline)

                # 3.4 执行交易
                for ts_code, target_shares in target_positions.items():
                    current_shares = self.positions.get(ts_code, 0)
                    if target_shares != current_shares:
                        kline_row = daily_kline[daily_kline['ts_code'] == ts_code]
                        if len(kline_row) == 0:
                            continue
                        kline_row = kline_row.iloc[0]
                        price = float(kline_row['close'])  # 使用收盘价
                        trade = self._execute_trade(date, ts_code, target_shares, price, current_shares)
                        if trade:
                            self.trades.append(trade)

                # 3.5 计算当日净值
                nav = self._calc_daily_nav(date, daily_kline)
                self.navs.append(nav)

                # 3.6 更新进度（每10%更新一次）
                if (idx + 1) % max(1, total_dates // 10) == 0 or idx == total_dates - 1:
                    progress = int((idx + 1) / total_dates * 100)
                    await self._update_progress(progress)

            except Exception as e:
                logger.error(f'回测日期 {date} 处理失败：{str(e)}', exc_info=True)
                raise

        # 4. 计算绩效指标
        logger.info('计算绩效指标...')
        metrics = self._calc_metrics()

        # 5. 保存结果
        await self._save_results(metrics)

        logger.info(f'回测完成，交易次数：{len(self.trades)}，最终净值：{metrics["final_equity"]:.2f}')
        return metrics

    async def _generate_online_signals(self, date: str, ts_codes: list[str]) -> dict[str, dict]:
        """在线模式：动态生成信号"""
        signals = {}
        try:
            # 获取因子数据
            predict_data = await ModelDataDao.get_training_data(
                self.db, self.feature_cols, ts_codes, date, date
            )
            if not predict_data:
                return signals

            df = pd.DataFrame(predict_data)
            if len(df) == 0:
                return signals

            # 准备特征
            X = df[self.feature_cols].copy()
            X = X.ffill().fillna(0)

            # 预测
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)[:, 1]

            # 构建信号字典
            for idx, row in df.iterrows():
                ts_code = row['ts_code']
                signals[ts_code] = {
                    'predict_label': int(predictions[idx]),
                    'predict_prob': float(probabilities[idx]),
                }
        except Exception as e:
            logger.warning(f'生成在线信号失败（日期：{date}）：{str(e)}')
        return signals

    def _generate_target_position(
        self, date: str, signals: dict[str, dict], daily_kline: pd.DataFrame
    ) -> dict[str, int]:
        """根据信号生成目标仓位"""
        target_positions = {}
        buy_threshold = float(self.task.signal_buy_threshold)
        sell_threshold = float(self.task.signal_sell_threshold)

        # 获取所有标的
        all_symbols = daily_kline['ts_code'].unique()

        if self.task.position_mode == 'equal_weight':
            # 等权重组合模式
            buy_signals = []
            for ts_code in all_symbols:
                signal = signals.get(ts_code, {})
                predict_prob = signal.get('predict_prob', 0.5)
                if predict_prob > buy_threshold:
                    buy_signals.append(ts_code)

            if buy_signals:
                # 计算每个标的的目标仓位（等权重）
                total_value = self.cash + sum(
                    self.positions.get(ts_code, 0) * float(daily_kline[daily_kline['ts_code'] == ts_code].iloc[0]['close'])
                    for ts_code in self.positions.keys()
                    if ts_code in daily_kline['ts_code'].values
                )
                target_value_per_stock = total_value * float(self.task.max_position) / len(buy_signals)

                for ts_code in buy_signals:
                    kline_row = daily_kline[daily_kline['ts_code'] == ts_code]
                    if len(kline_row) == 0:
                        continue
                    price = float(kline_row.iloc[0]['close'])
                    target_shares = int(target_value_per_stock / price / 100) * 100  # 按手（100股）取整
                    target_positions[ts_code] = max(0, target_shares)
        else:
            # 单票模式（暂不支持，默认等权重）
            for ts_code in all_symbols:
                signal = signals.get(ts_code, {})
                predict_prob = signal.get('predict_prob', 0.5)
                current_shares = self.positions.get(ts_code, 0)

                if predict_prob > buy_threshold:
                    # 买入/加仓
                    if current_shares == 0:
                        # 计算可买入数量
                        total_value = self.cash + sum(
                            self.positions.get(c, 0) * float(daily_kline[daily_kline['ts_code'] == c].iloc[0]['close'])
                            for c in self.positions.keys()
                            if c in daily_kline['ts_code'].values
                        )
                        kline_row = daily_kline[daily_kline['ts_code'] == ts_code]
                        if len(kline_row) == 0:
                            continue
                        price = float(kline_row.iloc[0]['close'])
                        target_value = total_value * float(self.task.max_position)
                        target_shares = int(target_value / price / 100) * 100
                        target_positions[ts_code] = max(0, target_shares)
                    else:
                        target_positions[ts_code] = current_shares
                elif predict_prob < sell_threshold:
                    # 卖出/减仓
                    target_positions[ts_code] = 0
                else:
                    # 保持仓位
                    target_positions[ts_code] = current_shares

        return target_positions

    def _execute_trade(
        self, date: str, ts_code: str, target_shares: int, price: float, current_shares: int
    ) -> dict[str, Any] | None:
        """执行单笔交易"""
        shares_diff = target_shares - current_shares

        if shares_diff == 0:
            return None

        # 计算滑点调整
        slippage = float(self.task.slippage_bp) / 10000.0
        if shares_diff > 0:
            # 买入：价格向上调整
            adjusted_price = price * (1 + slippage)
            side = 'buy'
        else:
            # 卖出：价格向下调整
            adjusted_price = price * (1 - slippage)
            side = 'sell'
            shares_diff = abs(shares_diff)

        # 计算交易金额
        amount = adjusted_price * shares_diff

        # 计算手续费
        commission_rate = float(self.task.commission_rate)
        fee = amount * commission_rate

        # 更新持仓和现金
        if side == 'buy':
            if self.cash < amount + fee:
                # 资金不足，调整交易数量
                available_cash = self.cash / (1 + commission_rate)
                shares_diff = int(available_cash / adjusted_price / 100) * 100
                if shares_diff <= 0:
                    return None
                amount = adjusted_price * shares_diff
                fee = amount * commission_rate

            self.cash -= amount + fee
            self.positions[ts_code] = current_shares + shares_diff
        else:
            self.cash += amount - fee
            if target_shares == 0:
                del self.positions[ts_code]
            else:
                self.positions[ts_code] = target_shares

        # 计算操作后状态
        position_after = self.positions.get(ts_code, 0)
        position_value_after = position_after * price
        equity_after = self.cash + sum(
            self.positions.get(c, 0) * price for c in self.positions.keys() if c == ts_code
        ) + sum(
            self.positions.get(c, 0) * price for c in self.positions.keys() if c != ts_code
        )

        trade = {
            'task_id': int(self.task.id),
            'trade_date': date,
            'trade_datetime': datetime.now(),
            'ts_code': ts_code,
            'side': side,
            'price': float(adjusted_price),
            'volume': shares_diff,
            'amount': float(amount),
            'fee': float(fee),
            'position_after': position_after,
            'position_value_after': float(position_value_after),
            'cash_after': float(self.cash),
            'equity_after': float(equity_after),
        }

        return trade

    def _calc_daily_nav(self, date: str, daily_kline: pd.DataFrame) -> dict[str, Any]:
        """计算当日净值"""
        # 计算持仓市值
        position_value = 0.0
        for ts_code, shares in self.positions.items():
            kline_row = daily_kline[daily_kline['ts_code'] == ts_code]
            if len(kline_row) > 0:
                price = float(kline_row.iloc[0]['close'])
                position_value += shares * price

        # 计算总资产
        total_equity = self.cash + position_value

        # 计算净值（相对于初始资金）
        initial_cash = float(self.task.initial_cash)
        nav = total_equity / initial_cash if initial_cash > 0 else 1.0

        return {
            'task_id': int(self.task.id),
            'trade_date': date,
            'nav': float(nav),
            'cash': float(self.cash),
            'position_value': float(position_value),
            'total_equity': float(total_equity),
        }

    def _calc_metrics(self) -> dict[str, Any]:
        """计算绩效指标"""
        if not self.navs:
            raise ValueError('净值数据为空')

        navs = sorted(self.navs, key=lambda x: x['trade_date'])
        nav_values = [n['nav'] for n in navs]

        # 总收益率
        total_return = (nav_values[-1] / nav_values[0]) - 1 if nav_values[0] > 0 else 0.0

        # 日收益率序列
        daily_returns = [
            (nav_values[i] / nav_values[i - 1]) - 1 for i in range(1, len(nav_values)) if nav_values[i - 1] > 0
        ]

        # 年化收益率
        days = len(nav_values)
        annual_return = ((1 + total_return) ** (252 / days)) - 1 if days > 0 else 0.0

        # 最大回撤
        peak = nav_values[0]
        max_drawdown = 0.0
        for nav in nav_values:
            if nav > peak:
                peak = nav
            drawdown = (peak - nav) / peak if peak > 0 else 0.0
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 年化波动率
        volatility = np.std(daily_returns) * np.sqrt(252) if len(daily_returns) > 0 else 0.0

        # 夏普比率（无风险利率设为0）
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0.0

        # 卡玛比率
        calmar_ratio = annual_return / max_drawdown if max_drawdown > 0 else 0.0

        # 胜率和盈亏比（基于交易明细）
        # 简化计算：基于交易方向判断盈亏
        buy_trades = [t for t in self.trades if t['side'] == 'buy']
        sell_trades = [t for t in self.trades if t['side'] == 'sell']

        # 计算每笔交易的盈亏（简化版）
        trade_profits = []
        position_cost = {}  # {ts_code: 成本价}

        for trade in sorted(self.trades, key=lambda x: (x['trade_date'], x['trade_datetime'])):
            ts_code = trade['ts_code']
            if trade['side'] == 'buy':
                # 买入：记录成本
                if ts_code not in position_cost:
                    position_cost[ts_code] = []
                position_cost[ts_code].append(trade['price'])
            elif trade['side'] == 'sell':
                # 卖出：计算盈亏
                if ts_code in position_cost and len(position_cost[ts_code]) > 0:
                    cost_price = position_cost[ts_code].pop(0)
                    profit = (trade['price'] - cost_price) * trade['volume'] - trade['fee']
                    trade_profits.append(profit)

        profitable_trades = [p for p in trade_profits if p > 0]
        loss_trades = [p for p in trade_profits if p < 0]
        win_rate = len(profitable_trades) / len(trade_profits) if trade_profits else 0.0
        avg_profit = np.mean(profitable_trades) if profitable_trades else 0.0
        avg_loss = abs(np.mean(loss_trades)) if loss_trades else 0.0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else 0.0

        # 构建净值曲线JSON
        equity_curve = [{'date': n['trade_date'], 'nav': n['nav']} for n in navs]

        return {
            'final_equity': float(nav_values[-1] * float(self.task.initial_cash)),
            'total_return': float(total_return),
            'annual_return': float(annual_return),
            'max_drawdown': float(max_drawdown),
            'volatility': float(volatility),
            'sharpe_ratio': float(sharpe_ratio),
            'calmar_ratio': float(calmar_ratio),
            'win_rate': float(win_rate),
            'profit_loss_ratio': float(profit_loss_ratio),
            'trade_count': len(self.trades),
            'equity_curve_json': json.dumps(equity_curve, ensure_ascii=False),
        }

    async def _update_progress(self, progress: int) -> None:
        """更新进度"""
        from module_backtest.dao.backtest_dao import BacktestTaskDao

        await BacktestTaskDao.update_task_status(self.db, int(self.task.id), self.task.status, progress=progress)
        await self.db.commit()

    async def _save_results(self, metrics: dict[str, Any]) -> None:
        """保存结果"""
        from module_backtest.dao.backtest_dao import BacktestResultDao

        # 保存结果汇总
        await BacktestResultDao.save_result(self.db, int(self.task.id), metrics)

        # 批量保存交易明细
        if self.trades:
            await BacktestResultDao.bulk_insert_trades(self.db, self.trades)

        # 批量保存净值日频数据
        if self.navs:
            await BacktestResultDao.bulk_insert_navs(self.db, self.navs)

        await self.db.commit()
