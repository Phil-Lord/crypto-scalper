SMA_CONFIG = {'short_window': 50, 'long_window': 200}
SMA_GRID = {'short_window': [10, 200], 'long_window': [100, 1000]}

PRECISION_TREND_CONFIG = {
    'short_ema': 72,
    'long_ema': 122,
    'rsi_window': 26,
    'rsi_oversold': 12.53,
    'rsi_overbought': 91.68,
    'adx_window': 14,
    'adx_threshold': 25,
    'atr_window': 14,
    'atr_threshold': 0.002,
    'weight_crossover': 0.25,
    'weight_rsi': 0.25,
    'weight_adx': 0.25,
    'weight_atr': 0.25,
    'buy_threshold': 0.38,
    'sell_threshold': -0.86
}
PRECISION_TREND_GRID = {
    'short_ema': [5, 50],
    'long_ema': [20, 500],
    'rsi_window': [5, 30],
    'rsi_oversold': [10.0, 40.0],
    'rsi_overbought': [60.0, 90.0],
    'adx_window': [5, 50],
    'adx_threshold': [10, 40],
    'atr_window': [5, 50],
    'atr_threshold': [0.001, 0.01],
    'weight_crossover': [0.0, 1.0],
    'weight_rsi': [0.0, 1.0],
    'weight_adx': [0.0, 1.0],
    'weight_atr': [0.0, 1.0],
    'buy_threshold': [0.0, 1.0],
    'sell_threshold': [-1.0, 0.0]
}
