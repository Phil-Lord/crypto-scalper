SMA_CONFIG = {'short_window': 50, 'long_window': 200}
SMA_GRID = {'short_window': [10, 200], 'long_window': [100, 1000]}

PRECISION_TREND_CONFIG = {
    'short_ema': 43,
    'long_ema': 79,
    'rsi_window': 27,
    'rsi_oversold': 16.810651415296164,
    'rsi_overbought': 67.28712660340719,
    'adx_window': 16,
    'adx_threshold': 21,
    'atr_window': 20,
    'atr_threshold': 0.008603916456060482,
    'weight_crossover': 0.112104129991123,
    'weight_rsi': 0.5762132330947007,
    'weight_adx': 0.4575004875564789,
    'weight_atr': 0.9312334277240586,
    'buy_threshold': 0.4858773351488588,
    'sell_threshold': -0.1288225552454357
}
PRECISION_TREND_GRID = {
    'short_ema': [10, 150],
    'long_ema': [60, 400],
    'rsi_window': [2, 20],
    'rsi_oversold': [5.0, 40.0],
    'rsi_overbought': [45.0, 70.0],
    'adx_window': [10, 100],
    'adx_threshold': [15, 60],
    'atr_window': [5, 50],
    # atr_threshold compares against ATR/close on 1-minute candles, where the ratio's median is
    # ~0.0003 and its 99th percentile ~0.002 (XXBTZGBP 2024-25) — thresholds above ~0.002 make
    # the ATR rule a permanent HOLD vote.
    'atr_threshold': [0.0002, 0.002],
    'weight_crossover': [0.1, 1.0],
    'weight_rsi': [0.1, 1.0],
    'weight_adx': [0.1, 1.0],
    'weight_atr': [0.1, 1.0],
    'buy_threshold': [0.1, 0.7],
    'sell_threshold': [-0.75, -0.05]
}
