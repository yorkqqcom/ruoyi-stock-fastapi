# -- coding: utf-8 --
import numpy as np
from fastapi import APIRouter, Depends, Query
from datetime import date

from fastapi.params import Body

from user_module.analyzer.enhanced_analysis_svm_time import EnhancedMarketAnalyzer
from user_module.services.stock_hist_service import StockHistService
from utils.response_util import ResponseUtil

stock_hist_router = APIRouter(prefix="/api/stock", tags=["个股历史行情"])
@stock_hist_router.get("/kline", response_model=dict)  # 修改路由为/kline
async def get_kline_data(
    symbol: str = Query(..., description="股票代码"),  # 修正描述
    start_date: date = Query(...),
    end_date: date = Query(...),
    adjust: str = Query(...),
):
    """
    获取K线图数据
    """
    results = await StockHistService.get_stock_history(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        adjust=adjust
    )
    return ResponseUtil.success(data=results.to_dict(orient="records"))  # 转换DataFrame为字典列表


@stock_hist_router.post("/analyze")
async def analyze_stock(
        symbol: str = Body(...),
        start_date: str = Body(...),
        end_date: str = Body(...)
):
    analyzer = EnhancedMarketAnalyzer(symbol)
    df = analyzer.fetch_market_data()
    analyzer.optimize_model(n_iter=1)
    signals = analyzer.generate_trading_signals()
    backtest_result = analyzer.backtest_strategy(holding_period=5)
    performance = backtest_result.get('performance', {})
    analysis_report = backtest_result.get('analysis_report', '')

    # 处理performance中的inf和NaN值
    def safe_convert(value):
        if isinstance(value, (np.generic, float)):
            v = float(value)
            if not np.isfinite(v):  # 检查是否为inf或NaN
                return None  # 替换为None或合适的默认值
            return v
        return value

    performance = {k: safe_convert(v) for k, v in performance.items()}

    # 处理signals中的数值
    signals_data = []
    for idx, row in signals.iterrows():
        if row['signal_type'] in ['BUY', 'SELL']:
            signal_entry = {
                "date": idx.strftime('%Y-%m-%d'),
                "type": str(row['signal_type']),
                "price": safe_convert(row['close_price']),
                "low": safe_convert(row['low']),
                "high": safe_convert(row['high'])
            }
            signals_data.append(signal_entry)

    stats = {
        "train_data_rows": int(len(df)),
        "volume_above_ma5": int((df['volume'] > df['volume'].rolling(5).mean()).sum()),
        "price_above_ma20": int((df['close'] > df['close'].rolling(20).mean()).sum()),
        "low_volatility": int((df['close'].pct_change().rolling(20).std() < 0.03).sum())
    }

    return ResponseUtil.success(data={
        "symbol": symbol,
        "signals": signals_data,
        "stats": stats,
        "performance": performance,
        "analysis_report": analysis_report
    })