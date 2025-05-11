from sqlalchemy import between
from datetime import date, datetime
import akshare as ak
from functools import lru_cache
import pandas as pd
FIELD_MAPPING = {
    "stock_zh_a_spot_em": {
        '代码': 'symbol',
        '名称': 'name',
        '最新价': 'price',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amt',
        '成交量': 'volume',
        '成交额': 'turnover',
        '振幅': 'amplitude',
        '最高': 'high',
        '最低': 'low',
        '今开': 'open',
        '昨收': 'pre_close',
        '量比': 'volume_ratio',
        '换手率': 'turnover_rate',
        '市盈率-动态': 'pe_ratio',
        '市净率': 'pb_ratio',
        '总市值': 'total_market_cap',
        '流通市值': 'circ_market_cap'
    },
    "stock_zh_a_hist": {
        '日期': 'date',
        '股票代码': 'symbol',
        '开盘': 'open',
        '收盘': 'close',
        '最高': 'high',
        '最低': 'low',
        '成交量': 'volume',
        '成交额': 'amount',
        '振幅': 'amplitude_pct',
        '涨跌幅': 'change_pct',
        '涨跌额': 'change_amt',
        '换手率': 'turnover_rate'
    }
}
class StockHistService:
    @staticmethod
    @lru_cache(maxsize=1)
    def _get_cached_stock_list(cache_key: str) -> pd.DataFrame:
        df = ak.stock_zh_a_spot_em()
        df = df.rename(columns=FIELD_MAPPING["stock_zh_a_spot_em"])
        df = df[['symbol', 'name']]
        return df

    @staticmethod
    async def get_stock_list():
        # 使用当前日期作为缓存键
        cache_key = datetime.now().strftime('%Y-%m-%d')
        return StockHistService._get_cached_stock_list(cache_key)

    @staticmethod
    async def get_stock_history(
            symbol: str = None,
            start_date: date = None,
            end_date: date = None,
            adjust: str = None,

    ):
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period='daily',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d'),
            adjust=adjust
        )
        df = df.rename(columns=FIELD_MAPPING["stock_zh_a_hist"])
        return df