import akshare as ak
import pandas as pd

class StockHistService:
    @staticmethod
    async def get_stock_spot_em():
        """获取A股实时行情数据"""
        try:
            df = ak.stock_zh_a_spot_em()
            return df[['代码', '名称', '最新价']].rename(columns={
                '代码': 'symbol',
                '名称': 'name',
                '最新价': 'price'
            })
        except Exception as e:
            print(f"获取股票行情失败: {str(e)}")
            return pd.DataFrame() 