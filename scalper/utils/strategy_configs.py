SMA_CONFIG = {'short_window': 50, 'long_window': 200}
SMA_GRID = {'short_window': [10, 200], 'long_window': [100, 1000]}

PRECISION_TREND_CONFIG = {
    'short_ema': 98,
    'long_ema': 172,
    'rsi_window': 14,
    'rsi_oversold': 50.0,
    'rsi_overbought': 50.0,
    'weight_crossover': 0.5,
    'weight_rsi': 0.5
}
PRECISION_TREND_GRID = {
    'short_ema': [5, 200],
    'long_ema': [50, 500],
    'rsi_window': [0, 50],
    'rsi_oversold': [0.0, 50.0],
    'rsi_overbought': [50.0, 100.0],
    'weight_crossover': [0.0, 1.0],
    'weight_rsi': [0.0, 1.0]
}
