from .strategies import (
    Strategy,
    SmaStrategy, SmaStrategyConfig,
    PrecisionTrendStrategy, PrecisionTrendStrategyConfig,
)


STRATEGIES = {
    'SmaStrategy': (SmaStrategy, SmaStrategyConfig),
    'PrecisionTrendStrategy': (PrecisionTrendStrategy, PrecisionTrendStrategyConfig),
}


def create_strategy(name: str, params: dict) -> Strategy:
    '''
    Create a strategy instance from name and parameters.

    :param name: Strategy class name (e.g., 'SmaStrategy').
    :param params: Dictionary of strategy configuration parameters.
    :return: Configured strategy instance.
    :raises ValueError: If strategy name is unknown.
    '''
    if name not in STRATEGIES:
        raise ValueError(f'Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}')

    strategy_cls, config_cls = STRATEGIES[name]
    config = config_cls(**params)
    return strategy_cls(config)
