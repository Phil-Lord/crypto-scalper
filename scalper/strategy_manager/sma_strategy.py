from .base_strategy import Strategy


class SmaStrategy(Strategy):
    def __init__(self, window_size: int):
        self.window_size = window_size
        self.prices = []

    def evaluate(self, price: float) -> str:
        return f'hold, price: £{price}'
