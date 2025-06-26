import json
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TradeRecord:
    symbol: str
    name: str
    buy_price: float
    shares: int
    buy_time: float
    sender_id: str
    sell_price: Optional[float] = None
    sell_time: Optional[float] = None

    def to_dict(self):
        return {
            'symbol': self.symbol,
            'name': self.name,
            'buy_price': self.buy_price,
            'shares': self.shares,
            'buy_time': self.buy_time,
            'sender_id': self.sender_id,
            'sell_price': self.sell_price,
            'sell_time': self.sell_time
        }

    @staticmethod
    def from_dict(data):
        return TradeRecord(
            symbol=data['symbol'],
            name=data['name'],
            buy_price=data['buy_price'],
            shares=data['shares'],
            buy_time=data['buy_time'],
            sender_id=data.get('sender_id', ''),
            sell_price=data.get('sell_price'),
            sell_time=data.get('sell_time')
        )

class TradeHistory:
    def __init__(self, file_path='trade_history.json'):
        self.file_path = file_path
        self.records: List[TradeRecord] = self._load_records()

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

    def add_buy_record(self, symbol: str, name: str, buy_price: float, shares: int, buy_time: float, sender_id: str) -> TradeRecord:
        """添加买入记录"""
        record = TradeRecord(
            symbol=symbol,
            name=name,
            buy_price=buy_price,
            shares=shares,
            buy_time=buy_time,
            sender_id=sender_id
        )
        self.records.append(record)
        self._save_records()
        return record

    def add_sell_record(self, symbol: str, shares: int, sell_price: float, sell_time: float) -> Optional[TradeRecord]:
        """添加卖出记录，返回匹配的买入记录"""
        # 获取该股票的所有未卖出记录
        open_positions = self.get_open_positions(symbol)
        if not open_positions:
            return None

        # 按买入时间排序，先进先出
        open_positions.sort(key=lambda x: x.buy_time)

        # 查找匹配的买入记录
        remaining_shares = shares
        matched_record = None

        for record in open_positions:
            if record.shares >= remaining_shares:
                # 找到匹配的记录
                matched_record = record
                matched_record.sell_price = sell_price
                matched_record.sell_time = sell_time
                break
            remaining_shares -= record.shares

        self._save_records()
        return matched_record

    def get_open_positions(self, symbol: Optional[str] = None) -> List[TradeRecord]:
        """获取未卖出的持仓记录"""
        positions = [r for r in self.records if r.sell_price is None]
        if symbol:
            positions = [r for r in positions if r.symbol == symbol]
        return positions

    def get_trade_history(self, symbol: Optional[str] = None) -> List[TradeRecord]:
        """获取所有交易记录"""
        records = self.records
        if symbol:
            records = [r for r in records if r.symbol == symbol]
        return records

    def to_dict(self):
        return {
            'records': [record.to_dict() for record in self.records]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            records=[TradeRecord.from_dict(record) for record in data['records']]
        )

    def to_dict(self):
        return {
            'records': [record.to_dict() for record in self.records]
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            records=[TradeRecord.from_dict(record) for record in data['records']]
        )