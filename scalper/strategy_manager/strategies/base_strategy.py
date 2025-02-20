from strategy_manager.indicators import Indicator
from strategy_manager.rules import Rule


class Strategy:
    def __init__(self):
        self.indicators: dict[str, Indicator] = {}
        self.rules: dict[str, Rule] = {}
        self.state = {'position': 'out'}
