from data_feed import DataFeed 
from modules import BacktestRunner, ResultAnalyzer, plot_results, DataHandler, TradeManager, StrategyEngine


# ----------------------------- 策略函数 -----------------------------
def ema_trend_strategy(row, instrument, initial_balance=100000, ema_windows=[5, 12, 20]):
    """
    EMA趋势策略：基于大趋势和小趋势进行交易，实时计算EMA。
    :param row: 当前 K 线数据
    :param instrument: 标的物代码
    :param initial_balance: 初始资金
    :param ema_windows: EMA的计算窗口，例如 [5, 12, 20]
    :return: 返回交易信号
    """
    # 获取当前价格
    price = row[f"{instrument}_15m_close"]
    
    # 初始化EMA计算器（如果尚未初始化）
    if not hasattr(ema_trend_strategy, 'ema_calculator'):
        ema_trend_strategy.ema_calculator = {}
        for window in ema_windows:
            ema_trend_strategy.ema_calculator[f"{instrument}_15m_ema_{window}"] = EMA(window)
            ema_trend_strategy.ema_calculator[f"{instrument}_1h_ema_{window}"] = EMA(window)
    
    # 更新EMA值
    for window in ema_windows:
        ema_trend_strategy.ema_calculator[f"{instrument}_15m_ema_{window}"].update(price)
        ema_trend_strategy.ema_calculator[f"{instrument}_1h_ema_{window}"].update(price)
    
    # 获取当前EMA值
    ema_5_15m = ema_trend_strategy.ema_calculator[f"{instrument}_15m_ema_5"].value
    ema_12_15m = ema_trend_strategy.ema_calculator[f"{instrument}_15m_ema_12"].value
    ema_12_1h = ema_trend_strategy.ema_calculator[f"{instrument}_1h_ema_12"].value
    ema_20_1h = ema_trend_strategy.ema_calculator[f"{instrument}_1h_ema_20"].value
    
    # 判断大趋势
    if ema_12_1h > ema_20_1h:
        major_trend = 'bull'
    elif ema_12_1h < ema_20_1h:
        major_trend = 'bear'
    else:
        major_trend = None
    
    # 判断小趋势
    if ema_5_15m > ema_12_15m:
        minor_trend = 'bull'
    elif ema_5_15m < ema_12_15m:
        minor_trend = 'bear'
    else:
        minor_trend = None
    
    # 初始化仓位和交易信号
    signal = None
    position = 0  # 当前仓位比例
    stop_loss = None  # 止损价格
    take_profit = None  # 止盈价格
    highest_price = None  # 最高价
    lowest_price = None  # 最低价
    
    # 多头趋势下的交易逻辑
    if major_trend == 'bull' and minor_trend == 'bull':
        if position == 0:
            # 首次开仓
            signal = 'buy'
            position = 0.2  # 20%仓位
            stop_loss = price * 0.9  # 初始止损
            highest_price = price  # 记录最高价
        elif position == 0.2 and price > highest_price * 1.1:
            # 加仓30%
            signal = 'buy'
            position = 0.5  # 50%仓位
            stop_loss = highest_price * 0.9  # 保持初始止损
            highest_price = price  # 更新最高价
        elif position == 0.5 and price > highest_price * 1.2:
            # 满仓
            signal = 'buy'
            position = 1.0  # 100%仓位
            stop_loss = highest_price * 0.9  # 保持初始止损
            highest_price = price  # 更新最高价
    
    # 空头趋势下的交易逻辑
    elif major_trend == 'bear' and minor_trend == 'bear':
        if position == 0:
            # 首次开仓
            signal = 'sell'
            position = 0.2  # 20%仓位
            stop_loss = price * 1.1  # 初始止损
            lowest_price = price  # 记录最低价
        elif position == 0.2 and price < lowest_price * 0.9:
            # 加仓30%
            signal = 'sell'
            position = 0.5  # 50%仓位
            stop_loss = lowest_price * 1.1  # 保持初始止损
            lowest_price = price  # 更新最低价
        elif position == 0.5 and price < lowest_price * 0.8:
            # 满仓
            signal = 'sell'
            position = 1.0  # 100%仓位
            stop_loss = lowest_price * 1.1  # 保持初始止损
            lowest_price = price  # 更新最低价
    
    # 检查止损条件
    if position > 0 and price <= stop_loss:
        signal = 'close'  # 平仓
    
    return signal


# ----------------------------- EMA计算器 -----------------------------
class EMA:
    def __init__(self, window):
        """
        初始化EMA计算器。
        :param window: EMA的窗口大小
        """
        self.window = window
        self.alpha = 2 / (window + 1)  # EMA的平滑系数
        self.value = None  # 当前EMA值
    
    def update(self, price):
        """
        更新EMA值。
        :param price: 当前价格
        """
        if self.value is None:
            self.value = price  # 初始值为第一个价格
        else:
            self.value = self.alpha * price + (1 - self.alpha) * self.value


# ----------------------------- 主程序 -----------------------------
if __name__ == "__main__":
    # 初始化数据接口
    datafeed = DataFeed(config_path=None, local_data_dir='./data/')

    # 初始化回测系统
    backtester = BacktestRunner(datafeed)
    backtester.set_parameters(
        instruments=['000300.XSHG'],
        periods=['15m', '1h'],
        start_time='2023-01-01',
        end_time='2023-12-31'
    )

    # 加载策略
    backtester.strategy_engine.load_strategy(ema_trend_strategy)

    # 运行回测
    backtester.run_backtest(instrument='000300.XSHG')

    # 生成回测报告
    analyzer = ResultAnalyzer(backtester.trade_manager.trades_log)
    report = analyzer.generate_report()
    print("回测报告:", report)

    # 可视化结果
    merged_data = backtester.data_handler.merge_data(['000300.XSHG'], ['15m', '1h'])
    plot_results(merged_data, backtester.trade_manager.trades_log, '000300.XSHG')
