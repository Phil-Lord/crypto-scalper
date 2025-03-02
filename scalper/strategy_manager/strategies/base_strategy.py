import pandas as pd

from strategy_manager.indicators import Indicator
from strategy_manager.rules import Rule


class Strategy:
    def __init__(self):
        self.indicators: dict[str, Indicator] = {}
        self.rules: dict[str, Rule] = {}
        self.last_action = 'sell'

    def register_indicator(self, name: str, indicator: Indicator):
        self.indicators[name] = indicator

    def register_rule(self, name: str, rule: Rule):
        self.rules[name] = rule

    def generate_signal(self, price: float) -> dict:
        ''' Compute indicators and rules given a new price, then generate signal. '''
        indicator_results = {
            name: indicator.update(price)
            for name, indicator in self.indicators.items()
        }
        rule_results = {
            rule_name: rule.check({**indicator_results, 'last_action': self.last_action})
            for rule_name, rule in self.rules.items()
        }
        signal = self._generate_signal(rule_results)
        if signal in ['buy', 'sell']:
            self.last_action = signal
        return {'price': price, **indicator_results, **rule_results, 'signal': signal}

    def vectorised_compute(self, prices: pd.Series) -> pd.DataFrame:
        ''' Compute indicators and rules for a series of prices, then generate signals. '''
        indicator_results = {
            name: indicator.compute_vectorised(prices)
            for name, indicator in self.indicators.items()
        }
        results = pd.DataFrame({'price': prices, **indicator_results})

        for rule_name, rule in self.rules.items():
            results[rule_name] = rule.compute_vectorised(results)

        return self._generate_signals(results)

    def _generate_signal(self, rule_results: dict) -> str:
        ''' Generate a signal based on the rule results of a training run interval. '''
        pass

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        ''' Generate signals based on the results of a vectorised trading run. '''
        pass
