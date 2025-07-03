SMA_CONFIG = {'short_window': 50, 'long_window': 200}
SMA_GRID = {'short_window': [10, 200], 'long_window': [100, 1000]}

PRECISION_TREND_CONFIG = {
    'short_ema': 14,
    'long_ema': 355,
    'rsi_window': 25,
    'rsi_oversold': 14.378242660658634,
    'rsi_overbought': 60.27413536013792,
    'adx_window': 30,
    'adx_threshold': 24,
    'atr_window': 47,
    'atr_threshold': 0.006820829143624696,
    'weight_crossover': 0.14401163202283473,
    'weight_rsi': 0.5008758383459028,
    'weight_adx': 0.19935665822072057,
    'weight_atr': 0.47998793341327217,
    'buy_threshold': 0.312015057851434,
    'sell_threshold': -0.4805304312328331
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
