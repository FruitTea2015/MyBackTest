import os
import pandas as pd
import matplotlib.pyplot as plt
from data_feed import DataFeed  # 假设这是您的数据接口模块

# ----------------------------- DataHandler 模块 -----------------------------
class DataHandler:
    def __init__(self, datafeed):
        """
        初始化 DataHandler，设置数据接口。
        :param datafeed: 数据接口对象
        """
        self.datafeed = datafeed

    def load_local_data(self, instrument, period):
        """
        读取指定标的物和周期的 K 线数据。
        :param instrument: 标的物代码，例如 '000300.XSHG'
        :param period: 周期，例如 '1m'（1 分钟）
        :return: 返回对应的 DataFrame
        """
        return self.datafeed.load_local_data(instrument, period)

    def merge_data(self, instruments, periods):
        """
        合并多个资产和周期的 K 线数据，按时间对齐。
        :param instruments: 标的物代码列表，例如 ['000300.XSHG', '000905.XSHG']
        :param periods: 周期列表，例如 ['1m', '5m']
        :return: 返回合并后的 DataFrame
        """
        merged_df = None
        for instrument in instruments:
            for period in periods:
                df = self.load_local_data(instrument, period)
                df = df.add_prefix(f"{instrument}_{period}_")  # 为列添加前缀以区分资产和周期
                if merged_df is None:
                    merged_df = df
                else:
                    merged_df = merged_df.join(df, how='outer')  # 按时间对齐合并
        return merged_df


# ----------------------------- StrategyEngine 模块 -----------------------------
class StrategyEngine:
    def __init__(self):
        """
        初始化 StrategyEngine。
        """
        self.strategy_function = None

    def load_strategy(self, strategy_function):
        """
        加载用户定义的策略函数。
        :param strategy_function: 用户定义的策略函数
        """
        self.strategy_function = strategy_function

    def run_strategy(self, data, start_time, end_time, **strategy_params):
        """
        在指定时间范围内运行策略。
        :param data: 合并后的 K 线数据 DataFrame
        :param start_time: 回测开始时间
        :param end_time: 回测结束时间
        :param strategy_params: 策略参数
        :return: 返回交易信号列表
        """
        if self.strategy_function is None:
            raise ValueError("未加载策略函数")
        
        signals = []
        filtered_data = data.loc[start_time:end_time]  # 过滤时间范围
        for idx, row in filtered_data.iterrows():
            signal = self.strategy_function(row, **strategy_params)  # 执行策略函数
            if signal:
                signals.append((idx, signal))  # 记录交易信号和时间
        return signals


# ----------------------------- TradeManager 模块 -----------------------------
class TradeManager:
    def __init__(self):
        """
        初始化 TradeManager。
        """
        self.trades_log = []
        self.positions = {}  # 记录当前持仓

    def execute_trade(self, signal, current_time, price, instrument):
        """
        记录交易执行信息。
        :param signal: 交易信号，例如 'buy' 或 'sell'
        :param current_time: 交易时间
        :param price: 交易价格
        :param instrument: 标的物代码
        """
        trade = {
            'instrument': instrument,
            'time': current_time,
            'signal': signal,
            'price': price,
            'stop_loss': price * 0.9 if signal == 'buy' else price * 1.1,  # 初始止损
            'take_profit': None,
            'highest_price': price if signal == 'buy' else None,  # 跟踪最高价
            'lowest_price': price if signal == 'sell' else None   # 跟踪最低价
        }
        self.trades_log.append(trade)
        self.positions[instrument] = trade  # 更新持仓

    def update_stop_loss(self, current_time, price_data):
        """
        更新止损止盈价格。
        :param current_time: 当前时间
        :param price_data: 当前价格数据
        """
        for instrument, position in self.positions.items():
            current_price = price_data[f"{instrument}_1m_close"]  # 假设使用 1 分钟周期的收盘价
            if position['signal'] == 'buy':
                position['highest_price'] = max(position['highest_price'], current_price)
                position['stop_loss'] = position['highest_price'] * 0.9  # 跟踪止损
            elif position['signal'] == 'sell':
                position['lowest_price'] = min(position['lowest_price'], current_price)
                position['stop_loss'] = position['lowest_price'] * 1.1  # 跟踪止损


# ----------------------------- ResultAnalyzer 模块 -----------------------------
class ResultAnalyzer:
    def __init__(self, trades_log):
        """
        初始化 ResultAnalyzer。
        :param trades_log: 交易记录
        """
        self.trades_log = trades_log

    def generate_report(self):
        """
        生成回测报告。
        :return: 返回回测报告字典
        """
        if not self.trades_log:
            return {}

        # 计算总收益
        initial_balance = 100000  # 初始资金
        balance = initial_balance
        for trade in self.trades_log:
            if trade['signal'] == 'buy':
                balance *= (trade['close_price'] / trade['price'])
            elif trade['signal'] == 'sell':
                balance *= (trade['price'] / trade['close_price'])

        total_return = (balance - initial_balance) / initial_balance
        return {
            'initial_balance': initial_balance,
            'final_balance': balance,
            'total_return': total_return
        }


# ----------------------------- BacktestRunner 模块 -----------------------------
class BacktestRunner:
    def __init__(self, datafeed):
        """
        初始化 BacktestRunner。
        :param datafeed: 数据接口对象
        """
        self.data_handler = DataHandler(datafeed)
        self.strategy_engine = StrategyEngine()
        self.trade_manager = TradeManager()

    def set_parameters(self, instruments, periods, start_time, end_time):
        """
        设置回测参数。
        :param instruments: 标的物代码列表
        :param periods: 周期列表
        :param start_time: 回测开始时间
        :param end_time: 回测结束时间
        """
        self.instruments = instruments
        self.periods = periods
        self.start_time = start_time
        self.end_time = end_time

    def run_backtest(self, **strategy_params):
        """
        运行回测流程。
        :param strategy_params: 策略参数
        """
        # 读取和合并数据
        merged_data = self.data_handler.merge_data(self.instruments, self.periods)

        # 运行策略
        signals = self.strategy_engine.run_strategy(merged_data, self.start_time, self.end_time, **strategy_params)

        # 记录交易
        for time, signal in signals:
            for instrument, action in signal.items():
                price = merged_data.loc[time][f"{instrument}_1m_close"]  # 假设使用 1 分钟周期的收盘价
                self.trade_manager.execute_trade(action, time, price, instrument)

        # 更新止损止盈
        for idx, row in merged_data.loc[self.start_time:self.end_time].iterrows():
            self.trade_manager.update_stop_loss(idx, row)


# ----------------------------- 可视化函数 -----------------------------
def plot_results(data, trades_log, instrument):
    """
    可视化回测结果。
    :param data: K 线数据
    :param trades_log: 交易记录
    :param instrument: 标的物代码
    """
    plt.figure(figsize=(12, 6))
    plt.plot(data.index, data[f"{instrument}_1m_close"], label='Price')
    for trade in trades_log:
        if trade['instrument'] == instrument:
            if trade['signal'] == 'buy':
                plt.scatter(trade['time'], trade['price'], color='green', label='Buy', marker='^')
            elif trade['signal'] == 'sell':
                plt.scatter(trade['time'], trade['price'], color='red', label='Sell', marker='v')
    plt.title(f'Backtest Results for {instrument}')
    plt.xlabel('Time')
    plt.ylabel('Price')
    plt.legend()
    plt.show()