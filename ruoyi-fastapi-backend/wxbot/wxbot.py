from wxpy import *
import time
from threading import Thread
from user_module.services.stock_hist_service import StockHistService
from trade_records import TradeHistory
from datetime import datetime, time as dt_time, timedelta
import pytz
import pandas_market_calendars as mcal
import signal

# 初始化微信机器人
bot = Bot()

# 初始化交易历史记录
trade_history = TradeHistory()

# 存储已提醒的记录，防止重复提醒
reminded_records = set()


# 获取A股交易日历
def get_trading_calendar():
    return mcal.get_calendar('SSE')  # 上海证券交易所日历


# 检查是否在交易时间内
def is_trading_time():
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    current_time = now.time()

    # 检查是否是交易日
    calendar = get_trading_calendar()
    trading_days = calendar.valid_days(start_date=now.date(), end_date=now.date())
    if len(trading_days) == 0:
        return False

    # 检查是否在交易时段内
    morning_start = dt_time(9, 15)
    morning_end = dt_time(11, 30)
    afternoon_start = dt_time(13, 0)
    afternoon_end = dt_time(15, 0)

    return (morning_start <= current_time <= morning_end) or \
        (afternoon_start <= current_time <= afternoon_end)


# 获取下一个交易日
def get_next_trading_day():
    now = datetime.now(pytz.timezone('Asia/Shanghai'))
    calendar = get_trading_calendar()
    next_trading_day = calendar.valid_days(start_date=now.date(), end_date=now.date() + timedelta(days=7))[0]
    return next_trading_day.date()


# 解析交易指令
def parse_trade_command(text):
    parts = text.split()
    if len(parts) == 4 and (parts[0] == "买入" or parts[0] == "卖出"):
        try:
            trade_type = parts[0]
            symbol = parts[1]
            price = float(parts[2])
            shares = int(parts[3])
            return trade_type, symbol, price, shares
        except:
            return None
    return None


# 格式化时间戳
def format_timestamp(timestamp):
    if isinstance(timestamp, (int, float)):
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return timestamp


# 处理消息并记录交易
@bot.register()
def handle_message(msg):
    if msg.type == TEXT:
        # 处理交易指令
        trade_result = parse_trade_command(msg.text)
        if trade_result:
            # 检查是否在交易时间内
            if not is_trading_time():
                next_trading_day = get_next_trading_day()
                msg.reply(f"当前不是交易时间，交易时间为工作日的9:15-11:30和13:00-15:00\n"
                          f"下一个交易日为：{next_trading_day}")
                return

            trade_type, symbol, price, shares = trade_result
            try:
                df = StockHistService.get_stock_spot_em()
                stock_info = df[df['symbol'] == symbol]
                if not stock_info.empty:
                    if trade_type == "买入":
                        record = trade_history.add_buy_record(
                            symbol=symbol,
                            name=stock_info.iloc[0]['name'],
                            buy_price=price,
                            shares=shares,
                            buy_time=msg.create_time
                        )
                        msg.reply(f"已记录买入：{stock_info.iloc[0]['name']}({symbol})\n"
                                  f"价格：{price} 数量：{shares}股")
                    else:  # 卖出
                        # 检查是否有对应的买入记录
                        open_positions = trade_history.get_open_positions(symbol)
                        if not open_positions:
                            msg.reply(f"未找到{symbol}的买入记录")
                            return

                        # 查找匹配的买入记录
                        record = trade_history.add_sell_record(
                            symbol=symbol,
                            shares=shares,
                            sell_price=price,
                            sell_time=msg.create_time
                        )

                        if record:
                            profit = (price - record.buy_price) * shares
                            profit_pct = (price - record.buy_price) / record.buy_price * 100
                            msg.reply(f"已记录卖出：{record.name}({symbol})\n"
                                      f"买入价：{record.buy_price} 卖出价：{price}\n"
                                      f"数量：{shares}股\n"
                                      f"盈亏：{profit:.2f}元 ({profit_pct:.2f}%)")
                        else:
                            msg.reply(f"未找到匹配的买入记录，请检查股票代码和数量是否正确")
                else:
                    msg.reply("股票代码无效")
            except Exception as e:
                msg.reply(f"处理交易失败：{str(e)}")
            return

        # 处理查询指令
        if msg.text.startswith("查询"):
            parts = msg.text.split()
            if len(parts) == 1:
                # 查询所有持仓
                positions = trade_history.get_open_positions()
                if positions:
                    response = "当前持仓情况：\n"
                    for pos in positions:
                        response += f"\n{pos.name}({pos.symbol})\n"
                        response += f"买入价：{pos.buy_price} 数量：{pos.shares}股\n"
                        response += f"买入时间：{format_timestamp(pos.buy_time)}\n"
                    msg.reply(response)
                else:
                    msg.reply("当前没有持仓")
                return

            if len(parts) == 2:
                symbol = parts[1]
                # 查询指定股票的持仓
                positions = trade_history.get_open_positions(symbol)
                if positions:
                    response = f"{symbol}当前持仓：\n"
                    for pos in positions:
                        response += f"\n{pos.name}({pos.symbol})\n"
                        response += f"买入价：{pos.buy_price} 数量：{pos.shares}股\n"
                        response += f"买入时间：{format_timestamp(pos.buy_time)}\n"
                    msg.reply(response)
                else:
                    msg.reply(f"未找到{symbol}的持仓记录")
                return

        # 处理历史交易查询
        if msg.text.startswith("历史"):
            parts = msg.text.split()
            if len(parts) == 1:
                # 查询所有历史交易
                history = trade_history.get_trade_history()
                if history:
                    response = "历史交易记录：\n"
                    for record in history:
                        response += f"\n{record.name}({record.symbol})\n"
                        response += f"买入：{record.buy_price}元 {record.shares}股 "
                        response += f"时间：{format_timestamp(record.buy_time)}\n"
                        if record.sell_price:
                            profit = (record.sell_price - record.buy_price) * record.shares
                            profit_pct = (record.sell_price - record.buy_price) / record.buy_price * 100
                            response += f"卖出：{record.sell_price}元 {record.shares}股 "
                            response += f"时间：{format_timestamp(record.sell_time)}\n"
                            response += f"盈亏：{profit:.2f}元 ({profit_pct:.2f}%)\n"
                    msg.reply(response)
                else:
                    msg.reply("暂无历史交易记录")
                return

            if len(parts) == 2:
                symbol = parts[1]
                # 查询指定股票的历史交易
                history = trade_history.get_trade_history(symbol)
                if history:
                    response = f"{symbol}历史交易记录：\n"
                    for record in history:
                        response += f"\n{record.name}({record.symbol})\n"
                        response += f"买入：{record.buy_price}元 {record.shares}股 "
                        response += f"时间：{format_timestamp(record.buy_time)}\n"
                        if record.sell_price:
                            profit = (record.sell_price - record.buy_price) * record.shares
                            profit_pct = (record.sell_price - record.buy_price) / record.buy_price * 100
                            response += f"卖出：{record.sell_price}元 {record.shares}股 "
                            response += f"时间：{format_timestamp(record.sell_time)}\n"
                            response += f"盈亏：{profit:.2f}元 ({profit_pct:.2f}%)\n"
                    msg.reply(response)
                else:
                    msg.reply(f"未找到{symbol}的历史交易记录")
                return

        # 默认回复
        msg.reply("请输入正确格式的指令：\n"
                  "买入 股票代码 价格 数量\n"
                  "卖出 股票代码 价格 数量\n"
                  "查询 [股票代码] - 查询当前持仓\n"
                  "历史 [股票代码] - 查询历史交易")


# 定时检查行情
def check_stock_profit():
    while True:
        try:
            # 检查是否在交易时间内
            if not is_trading_time():
                time.sleep(300)  # 非交易时间，5分钟后再次检查
                continue

            df = StockHistService.get_stock_spot_em()
            current_prices = df.set_index('symbol')['price'].to_dict()

            open_positions = trade_history.get_open_positions()
            for record in open_positions:
                current_price = current_prices.get(record.symbol)
                if current_price:
                    profit_pct = (current_price - record.buy_price) / record.buy_price * 100
                    if profit_pct >= 3:
                        # 生成唯一标识，用于防重复提醒
                        reminder_key = f"{record.symbol}_{record.buy_time}_{int(profit_pct)}"
                        if reminder_key not in reminded_records:
                            profit = (current_price - record.buy_price) * record.shares
                            bot.friends().search(record.name)[0].send(
                                f"【盈利提醒】{record.name}({record.symbol})\n"
                                f"当前涨幅：{profit_pct:.2f}%\n"
                                f"实现盈利：{profit:.2f}元"
                            )
                            reminded_records.add(reminder_key)
                            # 如果提醒记录过多，清理旧的记录
                            if len(reminded_records) > 1000:
                                reminded_records.clear()
        except Exception as e:
            print("检查行情失败:", str(e))
        time.sleep(300)  # 每5分钟检查一次


# 启动定时任务线程
Thread(target=check_stock_profit, daemon=True).start()


# 配置信号捕获
def graceful_exit(signum, frame):
    print("\n正在退出...")
    bot.logout()
    exit()


signal.signal(signal.SIGINT, graceful_exit)  # Ctrl+C
signal.signal(signal.SIGTERM, graceful_exit)  # kill 命令
# 启动（两种方式任选其一）
# bot.join()  # 方式1：阻塞式运行（推荐）
embed()  # 方式2：交互式运行

# bot.logout()