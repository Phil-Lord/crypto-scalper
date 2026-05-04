import numpy as np
import pandas as pd
import pytest

from backtesting_engine.backtesting_engine import BacktestingEngine
from backtesting_engine.window_evaluation import (
    evaluate_param_set_over_windows,
    run_strategy_on_window,
)
from data_system.models.trade_model import Trade
from strategy_manager.strategies.sma_strategy import SmaStrategy
from strategy_manager.strategies.sma_strategy_config import SmaStrategyConfig


@pytest.mark.backtesting_engine
@pytest.mark.window_evaluation
class TestRunStrategyOnWindow:
    def test_resets_strategy_then_sets_window_then_runs(self, mocker):
        # Given
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()
        start = pd.Timestamp('2021-01-01')
        end = pd.Timestamp('2021-04-01')

        # When
        run_strategy_on_window(engine, start, end)

        # Then
        engine.strategy.reset.assert_called_once_with()
        engine.set_ohlc_window.assert_called_once_with(start, end)
        engine.run.assert_called_once_with()


@pytest.mark.backtesting_engine
@pytest.mark.window_evaluation
class TestEvaluateParamSetOverWindows:
    @pytest.fixture
    def mock_engine(self, mocker):
        engine = mocker.Mock()
        engine.strategy = mocker.Mock()
        engine.strategy.__class__.__name__ = 'TestStrategy'
        return engine

    def test_creates_strategy_once_for_all_windows(self, mocker, mock_engine):
        # Given
        mock_create = mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            return_value=mocker.Mock(),
        )
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
            (pd.Timestamp('2021-03-01'), pd.Timestamp('2021-06-01')),
        ]

        # When
        evaluate_param_set_over_windows(mock_engine, {'sma_period': 10}, windows)

        # Then
        mock_create.assert_called_once_with('TestStrategy', {'sma_period': 10})

    def test_resets_strategy_between_windows(self, mocker, mock_engine):
        # Given
        new_strategy = mocker.Mock()
        mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            return_value=new_strategy,
        )
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
        ]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        assert new_strategy.reset.call_count == len(windows)

    def test_returns_balance_per_window_in_order(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        mock_engine.get_final_quote_balance.side_effect = [1100.0, 950.0, 1200.0]
        windows = [
            (pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01')),
            (pd.Timestamp('2021-02-01'), pd.Timestamp('2021-05-01')),
            (pd.Timestamp('2021-03-01'), pd.Timestamp('2021-06-01')),
        ]

        # When
        balances = evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        assert balances == [1100.0, 950.0, 1200.0]

    def test_passes_initial_balance_to_engine(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows, initial_balance=500)

        # Then
        mock_engine.get_final_quote_balance.assert_called_once_with(500)

    def test_default_initial_balance_is_1000(self, mocker, mock_engine):
        # Given
        mocker.patch('backtesting_engine.window_evaluation.create_strategy')
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When
        evaluate_param_set_over_windows(mock_engine, {}, windows)

        # Then
        mock_engine.get_final_quote_balance.assert_called_once_with(1000)

    def test_propagates_value_error_from_create_strategy(self, mocker, mock_engine):
        # Given
        mocker.patch(
            'backtesting_engine.window_evaluation.create_strategy',
            side_effect=ValueError('Invalid params'),
        )
        windows = [(pd.Timestamp('2021-01-01'), pd.Timestamp('2021-04-01'))]

        # When / Then — caller is responsible for translating ValueError.
        with pytest.raises(ValueError):
            evaluate_param_set_over_windows(mock_engine, {}, windows)


class _StubTradeRepository:
    '''
    Minimal repository stub returning a fixed list of trades — covers the
    surface of TradeRepository.get exercised by BacktestingEngine.
    '''

    def __init__(self, trades: list[Trade]) -> None:
        self._trades = trades

    def get(self, pair: str, start: float, end: float) -> list[Trade]:
        return self._trades


def _make_trades(pair: str, start_ts: float, count: int, seed: int) -> list[Trade]:
    '''
    Build deterministic minute-spaced trades with a price walk that crosses
    short/long SMAs, so MA crossover produces a non-trivial signal series.
    '''
    rng = np.random.default_rng(seed)
    prices = 100.0 + np.cumsum(rng.normal(0, 0.5, size=count))
    return [
        Trade(
            trade_id=i,
            pair=pair,
            price=float(price),
            volume=1.0,
            timestamp=start_ts + i * 60,
            side='b',
            order_type='m',
        )
        for i, price in enumerate(prices)
    ]


@pytest.mark.backtesting_engine
@pytest.mark.window_evaluation
class TestWindowParity:
    '''
    Real-engine parity test: running the engine on window A and then resetting
    + running on window B must produce identical output to running a freshly
    constructed engine on window B alone. Guards the per-window helper against
    state leakage across windows for both vectorised and live paths.
    '''

    PAIR = 'XXBTZGBP'

    @pytest.fixture
    def trades(self) -> list[Trade]:
        return _make_trades(pair=self.PAIR, start_ts=1609459200.0, count=120, seed=42)

    @pytest.fixture
    def windows(self) -> tuple[tuple[pd.Timestamp, pd.Timestamp], tuple[pd.Timestamp, pd.Timestamp]]:
        base = pd.Timestamp(1609459200, unit='s')
        window_a = (base, base + pd.Timedelta(minutes=29))
        window_b = (base + pd.Timedelta(minutes=60), base + pd.Timedelta(minutes=119))
        return window_a, window_b

    def _build_engine(self, trades: list[Trade], vectorised: bool) -> BacktestingEngine:
        config = SmaStrategyConfig(short_window=3, long_window=5)
        strategy = SmaStrategy(config)
        return BacktestingEngine(
            pair=self.PAIR,
            strategy=strategy,
            repository=_StubTradeRepository(trades),
            start=trades[0].timestamp,
            end=trades[-1].timestamp + 1,
            interval=1,
            vectorised=vectorised,
        )

    @pytest.mark.parametrize('vectorised', [True, False])
    def test_use_reset_run_b_matches_fresh_run_b(
        self, trades: list[Trade], windows, vectorised: bool,
    ) -> None:
        # Given
        window_a, window_b = windows

        # When — reuse engine: run window A, reset, run window B.
        reused = self._build_engine(trades, vectorised=vectorised)
        reused.set_ohlc_window(*window_a)
        reused.run()
        reused.strategy.reset()
        reused.set_ohlc_window(*window_b)
        reused_results = reused.run()

        # And — fresh engine: run window B only.
        fresh = self._build_engine(trades, vectorised=vectorised)
        fresh.set_ohlc_window(*window_b)
        fresh_results = fresh.run()

        # Then
        pd.testing.assert_frame_equal(reused_results, fresh_results)
