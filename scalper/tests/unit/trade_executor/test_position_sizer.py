from decimal import Decimal

import pytest

from data_system.models.bot_tick_model import Signal
from trade_executor.position_sizer import AllInPositionSizer, PairBalances


@pytest.mark.trade_executor
@pytest.mark.position_sizer
class TestPairBalances:
    @pytest.fixture
    def sample_balances(self) -> PairBalances:
        return PairBalances(
            symbol_base='XBT',
            symbol_quote='GBP',
            balance_base=Decimal('0.5'),
            balance_quote=Decimal('1000.00'),
        )

    def test_creates_pair_balances_with_correct_fields(self, sample_balances: PairBalances):
        assert sample_balances.symbol_base == 'XBT'
        assert sample_balances.symbol_quote == 'GBP'
        assert sample_balances.balance_base == Decimal('0.5')
        assert sample_balances.balance_quote == Decimal('1000.00')

    def test_pair_balances_is_frozen(self, sample_balances: PairBalances):
        with pytest.raises(AttributeError):
            sample_balances.balance_base = Decimal('1.0')


@pytest.mark.trade_executor
@pytest.mark.position_sizer
class TestAllInPositionSizer:
    @pytest.fixture
    def sizer(self) -> AllInPositionSizer:
        return AllInPositionSizer()

    @pytest.fixture
    def balances(self) -> PairBalances:
        return PairBalances(
            symbol_base='XBT',
            symbol_quote='GBP',
            balance_base=Decimal('0.5'),
            balance_quote=Decimal('1000.00'),
        )

    def test_buy_returns_full_quote_balance(self, sizer: AllInPositionSizer, balances: PairBalances):
        volume = sizer.calculate_volume(Signal.BUY, balances)
        assert volume == Decimal('1000.00')

    def test_sell_returns_full_base_balance(self, sizer: AllInPositionSizer, balances: PairBalances):
        volume = sizer.calculate_volume(Signal.SELL, balances)
        assert volume == Decimal('0.5')

    def test_hold_raises_value_error(self, sizer: AllInPositionSizer, balances: PairBalances):
        with pytest.raises(ValueError):
            sizer.calculate_volume(Signal.HOLD, balances)

    def test_buy_with_zero_quote_balance(self, sizer: AllInPositionSizer):
        # Given
        balances = PairBalances(
            symbol_base='XBT',
            symbol_quote='GBP',
            balance_base=Decimal('0.5'),
            balance_quote=Decimal('0'),
        )

        # When
        volume = sizer.calculate_volume(Signal.BUY, balances)

        # Then
        assert volume == Decimal('0')

    def test_sell_with_zero_base_balance(self, sizer: AllInPositionSizer):
        # Given
        balances = PairBalances(
            symbol_base='XBT',
            symbol_quote='GBP',
            balance_base=Decimal('0'),
            balance_quote=Decimal('1000.00'),
        )

        # When
        volume = sizer.calculate_volume(Signal.SELL, balances)

        # Then
        assert volume == Decimal('0')
