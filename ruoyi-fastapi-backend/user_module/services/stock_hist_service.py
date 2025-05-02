from sqlalchemy import between
from datetime import date
import akshare as ak
FIELD_MAPPING = {
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
    async def get_stock_history(
            symbol: str = None,
            start_date: date = None,
            end_date: date = None,
            adjust: str = None,

    ):
        print('------------start------------')
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period='daily',
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d'),
            adjust=adjust
        )
        df = df.rename(columns=FIELD_MAPPING["stock_zh_a_hist"])
        print(df)
        return df