from dataclasses import dataclass


@dataclass(frozen=True)
class PrecisionTrendStrategyConfig:
    '''
    Configuration for PrecisionTrendStrategy.

    Attributes:
        short_ema (int): Short EMA window size.
        long_ema (int): Long EMA window size.
        rsi_window (int): RSI calculation period.
        rsi_oversold (float): RSI oversold threshold.
        rsi_overbought (float): RSI overbought threshold.
        adx_window (int): ADX calculation period.
        adx_threshold (int): ADX threshold for trend strength.
        atr_window (int): ATR calculation period.
        atr_threshold (float): ATR threshold for volatility.
        weight_crossover (float): Weight for crossover signal.
        weight_rsi (float): Weight for RSI signal.
        weight_adx (float): Weight for ADX signal.
        weight_atr (float): Weight for ATR signal.
        buy_threshold (float): Score threshold for buy signals.
        sell_threshold (float): Score threshold for sell signals.
    '''
    # EMA parameters
    short_ema: int
    long_ema: int

    # RSI parameters
    rsi_window: int
    rsi_oversold: float
    rsi_overbought: float

    # ADX parameters
    adx_window: int
    adx_threshold: int

    # ATR parameters
    atr_window: int
    atr_threshold: float

    # Weightings
    weight_crossover: float = 1.0
    weight_rsi: float = 1.0
    weight_adx: float = 1.0
    weight_atr: float = 1.0

    # Thresholds
    buy_threshold: float = 0.5
    sell_threshold: float = -0.5

    def __post_init__(self):
        ''' Validate configuration constraints. '''
        if self.short_ema >= self.long_ema:
            raise ValueError(
                f'short_ema ({self.short_ema}) must be < long_ema ({self.long_ema})'
            )
        if self.rsi_oversold >= self.rsi_overbought:
            raise ValueError(
                f'rsi_oversold ({self.rsi_oversold}) must be < rsi_overbought ({self.rsi_overbought})'
            )
        if self.buy_threshold <= self.sell_threshold:
            raise ValueError(
                f'buy_threshold ({self.buy_threshold}) must be > sell_threshold ({self.sell_threshold})'
            )
