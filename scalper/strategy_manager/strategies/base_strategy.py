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

    def live_update(self, price: float) -> dict:
        indicator_values = {name: indicator.update(price)
                            for name, indicator in self.indicators.items()}

        signals = {}
        for rule_name, rule in self.rules.items():
            signals[rule_name] = rule.check({**indicator_values, **self.state})

        self.__update_state(signals)
        return {'signals': signals, 'indicators': indicator_values, 'price': price}

    def vectorised_compute(self, prices: pd.Series) -> pd.DataFrame:
        indicator_data = {
            name: indicator.compute_vectorised(prices)
            for name, indicator in self.indicators.items()
        }

        data = pd.DataFrame({'price': prices, **indicator_data})

        for rule_name, rule in self.rules.items():
            data[rule_name] = rule.compute_vectorised(data)

        return self.__simulate_state_transitions(data)

    def __update_state(self, signals: dict):
        pass

    def __simulate_state_transitions(self, data: pd.DataFrame) -> pd.DataFrame:
        pass
