from abc import ABC, abstractmethod

import numpy as np
import pandas as pd

from data_system import Signal

from strategy_manager.indicators import Indicator
from strategy_manager.rules import Rule


class Strategy(ABC):
    def __init__(self):
        self.indicators: dict[str, Indicator] = {}
        self.rules: dict[str, Rule] = {}
        self.last_action = Signal.SELL
        self.prev_indicator_values = {}

    def register_indicator(self, name: str, indicator: Indicator):
        self.indicators[name] = indicator

    def register_rule(self, name: str, rule: Rule):
        self.rules[name] = rule

    def generate_signal(self, ohlc: pd.Series) -> dict:
        ''' Compute indicators and rules given a new ohlc, then generate signal. '''
        indicator_results = {
            name: indicator.update(ohlc)
            for name, indicator in self.indicators.items()
        }

        current_state = {**indicator_results,
                         'last_action': self.last_action, **self.prev_indicator_values}
        rule_results = {
            rule_name: rule.check(current_state)
            for rule_name, rule in self.rules.items()
        }
        self.prev_indicator_values = {
            f'prev_{name}': value for name, value in indicator_results.items()
        }

        signal = self._generate_signal(rule_results)
        if signal == self.last_action and signal != Signal.HOLD:
            signal = Signal.HOLD
        else:
            if signal in (Signal.BUY, Signal.SELL):
                self.last_action = signal

        return {'price': ohlc['price'], **indicator_results, **rule_results, 'signal': signal}

    def vectorised_compute(self, ohlc: pd.DataFrame) -> pd.DataFrame:
        ''' Compute indicators and rules for a series of ohlc data, then generate signals. '''
        indicator_results = {
            name: indicator.compute_vectorised(ohlc)
            for name, indicator in self.indicators.items()
        }
        results = pd.DataFrame({'price': ohlc['price'], **indicator_results})

        for rule_name, rule in self.rules.items():
            results[rule_name] = rule.compute_vectorised(results)

        signals = self._generate_signals(results)
        results['signal'] = self._suppress_consecutive_signals(signals)
        return results

    @abstractmethod
    def _generate_signal(self, rule_results: dict) -> Signal:
        ''' Generate a signal based on the rule results of a training run interval. '''

    @abstractmethod
    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        ''' Generate signals based on the results of a vectorised trading run. '''

    def _suppress_consecutive_signals(self, signals: pd.Series) -> pd.Series:
        ''' Replace consecutive buy or sell signals with hold. '''
        signals_arr = signals.to_numpy()
        suppressed = np.empty_like(signals_arr, dtype=object)
        last_action = Signal.SELL

        for i, signal in enumerate(signals_arr):
            if signal == Signal.HOLD:
                suppressed[i] = Signal.HOLD
            elif signal == last_action:
                suppressed[i] = Signal.HOLD
            else:
                suppressed[i] = signal
                last_action = signal

        return pd.Series(suppressed, index=signals.index)

    def reset(self) -> None:
        ''' Reset strategy and all registered indicators to initial state. '''
        self.last_action = Signal.SELL
        self.prev_indicator_values = {}
        for indicator in self.indicators.values():
            indicator.reset()
