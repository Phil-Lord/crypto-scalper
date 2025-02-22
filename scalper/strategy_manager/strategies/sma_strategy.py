import numpy as np
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

    def _update_state(self, signals: dict):
        if signals['crossover'] == 'buy':
            self.state['position'] = 'long'
        elif signals['crossover'] == 'sell':
            self.state['position'] = 'out'

    def _simulate_state_transitions(self, data: pd.DataFrame) -> pd.DataFrame:
        df = data.copy()
        signals = df['crossover']

        # Create boolean masks for buy/sell signals.
        buy_signals = (signals == 'buy')
        sell_signals = (signals == 'sell')

        # Convert to numeric state changes (+1 buy, -1 sell) and calculate cumulative position state.
        state_changes = buy_signals.astype(int) - sell_signals.astype(int)
        cumulative_state = state_changes.cumsum().clip(lower=0, upper=1)

        # Map numeric states to position labels.
        df['position'] = np.where(cumulative_state, 'long', 'out')
        return df
