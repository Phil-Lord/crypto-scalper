import pandas as pd
import pytest

from backtesting_engine.profit_calculation import calculate_position_profits, get_final_quote_balance


@pytest.mark.backtesting_engine
@pytest.mark.profit_calculation
class TestCalculatePositionProfits:
    @pytest.fixture
    def sample_results_with_profit(self) -> pd.DataFrame:
        '''Results with a profitable buy-sell trade.'''
        return pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'sell', 'price': 110}
        ])

    @pytest.fixture
    def sample_results_no_trades(self) -> pd.DataFrame:
        '''Results with no trades (all holds).'''
        return pd.DataFrame([
            {'signal': 'hold', 'price': 100},
            {'signal': 'hold', 'price': 110}
        ])

    @pytest.fixture
    def sample_results_multiple_positions(self) -> pd.DataFrame:
        '''Results with multiple buy-sell cycles.'''
        return pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'sell', 'price': 105},
            {'signal': 'buy', 'price': 103},
            {'signal': 'sell', 'price': 108},
        ])

    @pytest.fixture
    def sample_results_incomplete_position(self) -> pd.DataFrame:
        '''Results with incomplete position (buy but no sell).'''
        return pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'hold', 'price': 110}
        ])

    def test_calculate_position_profits_buy_and_sell(self, sample_results_with_profit):
        # Given / When
        profits = calculate_position_profits(sample_results_with_profit)

        # Then
        assert len(profits) == 1
        assert 'profit' in profits.columns
        assert 'entry_time' in profits.columns
        assert 'exit_time' in profits.columns
        assert profits.iloc[0]['profit'] > 0

    def test_calculate_position_profits_no_trades(self, sample_results_no_trades):
        # Given / When
        profits = calculate_position_profits(sample_results_no_trades)

        # Then
        assert profits.empty

    def test_calculate_position_profits_multiple_positions(self, sample_results_multiple_positions):
        # Given / When
        profits = calculate_position_profits(sample_results_multiple_positions)

        # Then
        assert len(profits) == 2
        assert all(profits['profit'] > 0)

    def test_calculate_position_profits_incomplete_position(self, sample_results_incomplete_position):
        # Given / When
        profits = calculate_position_profits(sample_results_incomplete_position)

        # Then - Incomplete positions should not be included
        assert profits.empty

    def test_calculate_position_profits_with_loss(self):
        # Given
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 110},
            {'signal': 'sell', 'price': 100}
        ])

        # When
        profits = calculate_position_profits(results)

        # Then
        assert len(profits) == 1
        assert profits.iloc[0]['profit'] < 0

    def test_calculate_position_profits_custom_initial_balance(self, sample_results_with_profit):
        # Given
        initial_balance = 5000

        # When
        profits = calculate_position_profits(sample_results_with_profit, initial_balance)

        # Then
        assert len(profits) == 1
        # Larger initial balance should lead to larger absolute profit
        assert abs(profits.iloc[0]['profit']) > 0

    def test_calculate_position_profits_default_fee_is_taker(self, sample_results_with_profit):
        # Given - explicit taker fee matches the default
        explicit = calculate_position_profits(sample_results_with_profit, fee=0.004)

        # When
        defaulted = calculate_position_profits(sample_results_with_profit)

        # Then
        assert defaulted.iloc[0]['profit'] == pytest.approx(explicit.iloc[0]['profit'])

    def test_calculate_position_profits_maker_fee_beats_taker(self, sample_results_with_profit):
        # When - lower maker fee leaves more profit than the taker default
        maker = calculate_position_profits(sample_results_with_profit, fee=0.0016)
        taker = calculate_position_profits(sample_results_with_profit, fee=0.004)

        # Then
        assert maker.iloc[0]['profit'] > taker.iloc[0]['profit']

    def test_calculate_position_profits_fee_applied_both_sides(self):
        # Given - buy and sell at the same price isolates the fee impact
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100.0},
            {'signal': 'sell', 'price': 100.0},
        ])
        fee = 0.0016
        initial = 1000.0

        # When
        profits = calculate_position_profits(results, initial, fee=fee)

        # Then - fee is charged on both the buy and the sell
        base = (initial / 100.0) * (1 - fee)
        expected = base * 100.0 * (1 - fee) - (100.0 * base)
        assert profits.iloc[0]['profit'] == pytest.approx(expected, rel=1e-9)


@pytest.mark.backtesting_engine
@pytest.mark.profit_calculation
class TestGetFinalQuoteBalance:
    @pytest.fixture
    def sample_results_with_profit(self) -> pd.DataFrame:
        '''Results with a profitable buy-sell trade.'''
        return pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'sell', 'price': 110}
        ])

    @pytest.fixture
    def sample_results_no_trades(self) -> pd.DataFrame:
        '''Results with no trades (all holds).'''
        return pd.DataFrame([
            {'signal': 'hold', 'price': 100},
            {'signal': 'hold', 'price': 110}
        ])

    def test_get_final_quote_balance_with_profit(self, sample_results_with_profit):
        # Given / When
        balance = get_final_quote_balance(sample_results_with_profit)

        # Then
        assert balance > 1000  # Should be more than initial

    def test_get_final_quote_balance_no_trades(self, sample_results_no_trades):
        # Given / When
        balance = get_final_quote_balance(sample_results_no_trades)

        # Then
        assert balance == 1000  # Should equal initial

    def test_get_final_quote_balance_with_loss(self):
        # Given
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 110},
            {'signal': 'sell', 'price': 100}
        ])

        # When
        balance = get_final_quote_balance(results)

        # Then
        assert balance < 1000  # Should be less than initial

    def test_get_final_quote_balance_incomplete_position(self):
        # Given - Buy but no sell, price goes up
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'hold', 'price': 110}
        ])

        # When
        balance = get_final_quote_balance(results)

        # Then - Should value position at final price
        assert balance > 1000

    def test_get_final_quote_balance_custom_initial_balance(self, sample_results_with_profit):
        # Given
        initial_balance = 5000

        # When
        balance = get_final_quote_balance(sample_results_with_profit, initial_balance)

        # Then
        assert balance > initial_balance

    def test_get_final_quote_balance_fees_applied(self):
        # Given - Exact prices that should demonstrate fee impact
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100},
            {'signal': 'sell', 'price': 100}  # Same price
        ])

        # When
        balance = get_final_quote_balance(results)

        # Then - Should be less than initial due to fees (0.4% x 2)
        assert balance < 1000
        # Approximately 0.8% loss
        assert balance > 1000 * 0.99

    def test_get_final_quote_balance_open_position_applies_exit_fee(self):
        # Given - Buy but no sell, final price equals buy price (isolates fee behaviour)
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100.0},
            {'signal': 'hold', 'price': 100.0},
        ])
        fee = 0.004
        initial = 1000.0

        # When
        balance = get_final_quote_balance(results, initial)

        # Then - Exit fee is applied: initial * (1-fee) on buy, * (1-fee) on final valuation
        # base_balance = (1000 / 100) * (1 - 0.004) = 9.96
        # final = 9.96 * 100 * (1 - 0.004) = 992.0160
        base = (initial / 100.0) * (1 - fee)
        expected = base * 100.0 * (1 - fee)
        assert balance == pytest.approx(expected, rel=1e-9)

    def test_get_final_quote_balance_default_fee_is_taker(self, sample_results_with_profit):
        # Given - explicit taker fee matches the default
        explicit = get_final_quote_balance(sample_results_with_profit, fee=0.004)

        # When
        defaulted = get_final_quote_balance(sample_results_with_profit)

        # Then
        assert defaulted == pytest.approx(explicit)

    def test_get_final_quote_balance_maker_fee_beats_taker(self, sample_results_with_profit):
        # When - lower maker fee leaves a higher final balance than the taker default
        maker = get_final_quote_balance(sample_results_with_profit, fee=0.0016)
        taker = get_final_quote_balance(sample_results_with_profit, fee=0.004)

        # Then
        assert maker > taker

    def test_get_final_quote_balance_maker_fee_exact(self):
        # Given - same-price round trip isolates the fee impact at maker rate
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100.0},
            {'signal': 'sell', 'price': 100.0},
        ])
        fee = 0.0016
        initial = 1000.0

        # When
        balance = get_final_quote_balance(results, initial, fee=fee)

        # Then - both sides charged: 1000 * (1-fee)^2
        expected = initial * (1 - fee) ** 2
        assert balance == pytest.approx(expected, rel=1e-9)
