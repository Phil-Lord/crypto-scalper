import numpy as np
import pandas as pd

from data_system import Signal

from .base_strategy import Strategy
from .precision_trend_strategy_config import PrecisionTrendStrategyConfig
from strategy_manager.indicators import AdxIndicator, AtrIndicator, EmaIndicator, RsiIndicator
from strategy_manager.rules import AdxThresholdRule, AtrThresholdRule, MaCrossoverRule, RsiThresholdRule


class PrecisionTrendStrategy(Strategy):
    ''' EMA crossover, RSI, ADX, ATR '''

    def __init__(self, config: PrecisionTrendStrategyConfig):
        super().__init__()
        self.config = config
        total_weight = (config.weight_crossover + config.weight_rsi +
                        config.weight_adx + config.weight_atr)
        self.buy_threshold = config.buy_threshold
        self.sell_threshold = config.sell_threshold

        self.register_indicator('short_ema', EmaIndicator(config.short_ema))
        self.register_indicator('long_ema', EmaIndicator(config.long_ema))
        self.register_rule('crossover', MaCrossoverRule('short_ema', 'long_ema'))
        self.weight_crossover = config.weight_crossover / total_weight

        self.register_indicator('rsi', RsiIndicator(config.rsi_window))
        self.register_rule('rsi_threshold', RsiThresholdRule(
            'rsi', config.rsi_oversold, config.rsi_overbought))
        self.weight_rsi = config.weight_rsi / total_weight

        self.register_indicator('adx', AdxIndicator(config.adx_window))
        self.register_rule('adx_threshold', AdxThresholdRule('adx', config.adx_threshold))
        self.weight_adx = config.weight_adx / total_weight

        self.register_indicator('atr', AtrIndicator(config.atr_window))
        self.register_rule('atr_threshold', AtrThresholdRule('atr', config.atr_threshold))
        self.weight_atr = config.weight_atr / total_weight

    @property
    def warmup_candles(self) -> int:
        ''' The 3x multiplier is the standard EMA convergence heuristic. '''
        return 3 * max(
            self.config.short_ema,
            self.config.long_ema,
            self.config.rsi_window,
            self.config.adx_window,
            self.config.atr_window
        )

    def _generate_signal(self, rule_results: dict) -> Signal:
        crossover_signal = rule_results['crossover']
        rsi_threshold_signal = rule_results['rsi_threshold']
        adx_threshold_signal = rule_results['adx_threshold']
        atr_threshold_signal = rule_results['atr_threshold']

        signal_map = {Signal.BUY: 1, Signal.HOLD: 0, Signal.SELL: -1}
        score = (self.weight_crossover * signal_map[crossover_signal] +
                 self.weight_rsi * signal_map[rsi_threshold_signal] +
                 self.weight_adx * signal_map[adx_threshold_signal] +
                 self.weight_atr * signal_map[atr_threshold_signal])

        if score > self.buy_threshold:
            return Signal.BUY
        elif score < self.sell_threshold:
            return Signal.SELL
        else:
            return Signal.HOLD

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        signal_map = {Signal.BUY: 1, Signal.HOLD: 0, Signal.SELL: -1}
        indicators = {
            'crossover': self.weight_crossover,
            'rsi_threshold': self.weight_rsi,
            'adx_threshold': self.weight_adx,
            'atr_threshold': self.weight_atr
        }
        total_scores = sum(
            results[indicator].map(signal_map) * weight
            for indicator, weight in indicators.items()
        )

        conditions = [total_scores > self.buy_threshold, total_scores < self.sell_threshold]
        choices = ['buy', 'sell']  # Use strings as np.select truncates enums
        result_str = np.select(conditions, choices, default='hold')

        signal_map_reverse = {'buy': Signal.BUY, 'hold': Signal.HOLD, 'sell': Signal.SELL}
        result = pd.Series([signal_map_reverse[s] for s in result_str], index=results.index)
        return result
