import pandas as pd

from .base_strategy import Strategy
from strategy_manager.indicators import SmaIndicator
from strategy_manager.rules import MaCrossoverRule


class SmaStrategy(Strategy):
    def __init__(self, short_window: int, long_window: int):
        super().__init__()
        self.register_indicator('short_sma', SmaIndicator(short_window))
        self.register_indicator('long_sma', SmaIndicator(long_window))
        self.register_rule('crossover', MaCrossoverRule('short_sma', 'long_sma'))

    def __update_state(self, signals: dict):
        if signals['crossover'] == 'buy':
            self.state['position'] = 'long'
        elif signals['crossover'] == 'sell':
            self.state['position'] = 'out'

    def _simulate_state_transitions(self, data: pd.DataFrame) -> pd.DataFrame:
        data['position'] = 'out'
        in_position = False

        for i in range(len(data)):
            signal = data['crossover'].iloc[i]

            if signal == 'buy' and not in_position:
                data['position'].iloc[i] = 'long'
                in_position = True
            elif signal == 'sell' and in_position:
                data['position'].iloc[i] = 'out'
                in_position = False
            else:
                data['position'].iloc[i] = data['position'].iloc[i-1] if i > 0 else 'out'

        return data
