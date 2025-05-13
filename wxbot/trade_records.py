import json
import os
from datetime import datetime

class TradeRecord:
    def __init__(self, symbol, name, buy_price, shares, buy_time, sell_price=None, sell_time=None):
        self.symbol = symbol
        self.name = name
        self.buy_price = buy_price
        self.shares = shares
        self.buy_time = buy_time
        self.sell_price = sell_price
        self.sell_time = sell_time

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name': self.name,
            'buy_price': self.buy_price,
            'shares': self.shares,
            'buy_time': self.buy_time,
            'sell_price': self.sell_price,
            'sell_time': self.sell_time
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            symbol=data['symbol'],
            name=data['name'],
            buy_price=data['buy_price'],
            shares=data['shares'],
            buy_time=data['buy_time'],
            sell_price=data.get('sell_price'),
            sell_time=data.get('sell_time')
        )

class TradeHistory:
    def __init__(self, file_path='trade_history.json'):
        self.file_path = file_path
        self.records = self._load_records()

    def _load_records(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    return [TradeRecord.from_dict(record) for record in json.load(f)]
            except Exception as e:
                print(f"加载交易记录失败: {str(e)}")
                return []
        return []

    def _save_records(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump([record.to_dict() for record in self.records], f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存交易记录失败: {str(e)}")

    def add_buy_record(self, symbol, name, buy_price, shares, buy_time):
        record = TradeRecord(symbol, name, buy_price, shares, buy_time)
        self.records.append(record)
        self._save_records()
        return record

    def add_sell_record(self, symbol, shares, sell_price, sell_time):
        # 查找未配对的买入记录
        for record in self.records:
            if (record.symbol == symbol and 
                record.shares == shares and 
                record.sell_price is None):
                record.sell_price = sell_price
                record.sell_time = sell_time
                self._save_records()
                return record
        return None

    def get_open_positions(self, symbol=None):
        if symbol:
            return [r for r in self.records if r.symbol == symbol and r.sell_price is None]
        return [r for r in self.records if r.sell_price is None]

    def get_trade_history(self, symbol=None):
        if symbol:
            return [r for r in self.records if r.symbol == symbol]
        return self.records 