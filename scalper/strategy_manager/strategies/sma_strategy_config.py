from dataclasses import dataclass


@dataclass(frozen=True)
class SmaStrategyConfig:
    '''
    Configuration for SmaStrategy.

    Attributes:
        short_window (int): Short SMA window size.
        long_window (int): Long SMA window size.
    '''
    short_window: int
    long_window: int

    def __post_init__(self):
        ''' Validate configuration constraints. '''
        if self.short_window >= self.long_window:
            raise ValueError(
                f'short_window ({self.short_window}) must be < long_window ({self.long_window})'
            )
