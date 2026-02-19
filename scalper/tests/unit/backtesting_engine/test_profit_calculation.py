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

        # Then - Should be less than initial due to fees (0.04% x 2)
        assert balance < 1000
        # Approximately 0.08% loss
        assert balance > 1000 * 0.99

    def test_get_final_quote_balance_open_position_applies_exit_fee(self):
        # Given - Buy but no sell, final price equals buy price (isolates fee behaviour)
        results = pd.DataFrame([
            {'signal': 'buy', 'price': 100.0},
            {'signal': 'hold', 'price': 100.0},
        ])
        fee = 0.0004
        initial = 1000.0

        # When
        balance = get_final_quote_balance(results, initial)

        # Then - Exit fee is applied: initial * (1-fee) on buy, * (1-fee) on final valuation
        # base_balance = (1000 / 100) * (1 - 0.0004) = 9.9996
        # final = 9.9996 * 100 * (1 - 0.0004) = 999.560016
        base = (initial / 100.0) * (1 - fee)
        expected = base * 100.0 * (1 - fee)
        assert balance == pytest.approx(expected, rel=1e-9)
