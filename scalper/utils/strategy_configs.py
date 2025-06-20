SMA_CONFIG = {'short_window': 50, 'long_window': 200}
SMA_GRID = {'short_window': [10, 200], 'long_window': [100, 1000]}

PRECISION_TREND_CONFIG = {
    'short_ema': 72,
    'long_ema': 122,
    'rsi_window': 26,
    'rsi_oversold': 12.53,
    'rsi_overbought': 91.68,
    'weight_crossover': 0.04,
    'weight_rsi': 0.87,
    'buy_threshold': 0.38,
    'sell_threshold': -0.86
}
PRECISION_TREND_GRID = {
    'short_ema': [5, 200],
    'long_ema': [50, 500],
    'rsi_window': [0, 50],
    'rsi_oversold': [0.0, 50.0],
    'rsi_overbought': [50.0, 100.0],
    'weight_crossover': [0.0, 1.0],
    'weight_rsi': [0.0, 1.0],
    'buy_threshold': [0.0, 1.0],
    'sell_threshold': [-1.0, 0.0]
}
