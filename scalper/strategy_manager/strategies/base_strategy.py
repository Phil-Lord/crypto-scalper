import pandas as pd

from strategy_manager.indicators import Indicator
from strategy_manager.rules import Rule


class Strategy:
    def __init__(self):
        self.indicators: dict[str, Indicator] = {}
        self.rules: dict[str, Rule] = {}
        self.state = {'position': 'out'}

    def register_indicator(self, name: str, indicator: Indicator):
        self.indicators[name] = indicator

    def register_rule(self, name: str, rule: Rule):
        self.rules[name] = rule

    def generate_signal(self, price: float) -> dict:
        indicator_values = {name: indicator.update(price)
                            for name, indicator in self.indicators.items()}

        signals = {}
        for rule_name, rule in self.rules.items():
            signals[rule_name] = rule.check({**indicator_values, **self.state})

        self._update_state(signals)
        return {'signals': signals, 'indicators': indicator_values, 'price': price}

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

    def _update_state(self, signals: dict):
        pass

    def _generate_signals(self, results: pd.DataFrame) -> pd.DataFrame:
        ''' Generates signals based the results of a vectorised trading run. '''
        pass
