# Add-Strategy Templates

Copy the relevant block, drop it into the file path noted, and replace every `{{placeholder}}`
with the new strategy's specifics. Templates are intentionally minimal — extend them where the
strategy genuinely needs more (e.g. multi-rule weighting, see `precision_trend_strategy.py`).

---

## Strategy config

Path: `scalper/strategy_manager/strategies/{{name}}_strategy_config.py`

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class {{Name}}StrategyConfig:
    '''
    Configuration for {{Name}}Strategy.

    Attributes:
        {{param_a}} ({{type_a}}): {{description of param_a}}.
        {{param_b}} ({{type_b}}): {{description of param_b}}.
    '''
    {{param_a}}: {{type_a}}
    {{param_b}}: {{type_b}}

    def __post_init__(self):
        ''' Validate configuration constraints. '''
        if self.{{param_a}} >= self.{{param_b}}:
            raise ValueError(
                f'{{param_a}} ({self.{{param_a}}}) must be < '
                f'{{param_b}} ({self.{{param_b}}})'
            )
```

---

## Strategy class

Path: `scalper/strategy_manager/strategies/{{name}}_strategy.py`

```python
import pandas as pd

from data_system import Signal

from .base_strategy import Strategy
from .{{name}}_strategy_config import {{Name}}StrategyConfig
from strategy_manager.indicators import {{IndicatorClass}}
from strategy_manager.rules import {{RuleClass}}


class {{Name}}Strategy(Strategy):
    ''' {{One-line summary of what this strategy does}} '''

    def __init__(self, config: {{Name}}StrategyConfig):
        super().__init__()
        self.config = config
        self.register_indicator('{{indicator_name}}', {{IndicatorClass}}(config.{{param}}))
        self.register_rule('{{rule_name}}', {{RuleClass}}('{{indicator_name}}'))

    @property
    def warmup_candles(self) -> int:
        '''
        {{Explain why this many candles are needed — e.g. longest indicator window plus rule
        lookback.}}
        '''
        return self.config.{{param}} + 1

    def _generate_signal(self, rule_results: dict) -> Signal:
        ''' Live: called once per OHLC bar. '''
        return rule_results['{{rule_name}}']

    def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
        ''' Vectorised: called with full historical DataFrame for backtesting. '''
        return results['{{rule_name}}']
```

---

## Strategy unit tests

Path: `scalper/tests/unit/strategy_manager/strategies/test_{{name}}_strategy.py`

```python
import numpy as np
import pandas as pd
import pytest

from data_system.models.bot_tick_model import Signal
from strategy_manager.strategies.{{name}}_strategy import {{Name}}Strategy
from strategy_manager.strategies.{{name}}_strategy_config import {{Name}}StrategyConfig


@pytest.mark.strategy_manager
@pytest.mark.strategies
@pytest.mark.{{name}}_strategy
class Test{{Name}}Strategy:
    @pytest.fixture
    def strategy(self) -> {{Name}}Strategy:
        config = {{Name}}StrategyConfig({{param_a}}={{value_a}}, {{param_b}}={{value_b}})
        return {{Name}}Strategy(config)

    def test_initialisation_registers_indicators_and_rules(self, strategy: {{Name}}Strategy):
        assert '{{indicator_name}}' in strategy.indicators
        assert '{{rule_name}}' in strategy.rules

    def test_config_rejects_invalid_{{param_a}}(self):
        with pytest.raises(ValueError, match='{{param_a}}'):
            {{Name}}StrategyConfig({{param_a}}={{invalid_a}}, {{param_b}}={{value_b}})

    def test_generate_signal_returns_buy_when_rule_is_buy(self, strategy: {{Name}}Strategy):
        # Given
        rule_results = {'{{rule_name}}': Signal.BUY}

        # When
        signal = strategy._generate_signal(rule_results)

        # Then
        assert signal == Signal.BUY

    def test_generate_signals_returns_correct_series(self, strategy: {{Name}}Strategy):
        # Given
        results = pd.DataFrame({
            '{{rule_name}}': [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]
        })

        # When
        signals = strategy._generate_signals(results)

        # Then
        assert isinstance(signals, pd.Series)
        assert list(signals) == [Signal.BUY, Signal.HOLD, Signal.SELL, Signal.HOLD]

    def test_live_and_vectorised_produce_identical_signals(self, strategy: {{Name}}Strategy):
        '''
        Dual-implementation parity check (see .claude/rules/architecture.md). Both paths must
        produce identical signals on identical data.
        '''
        # Given
        np.random.seed(42)
        prices = np.linspace(100, 120, 50)
        ohlc = pd.DataFrame({'close': prices})

        # When
        live_signals = [
            strategy.generate_signal(pd.Series({'close': p}))['signal']
            for p in prices
        ]
        strategy.reset()
        vectorised = strategy.vectorised_compute(ohlc)

        # Then
        assert list(vectorised['signal']) == live_signals
```
