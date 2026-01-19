from utils import PRECISION_TREND_CONFIG


def load_config():
    return {
        'pair': 'BTC/USD',
        'interval': 1,
        'strategy_name': 'PrecisionTrendStrategy',
        'strategy_params': PRECISION_TREND_CONFIG
    }
