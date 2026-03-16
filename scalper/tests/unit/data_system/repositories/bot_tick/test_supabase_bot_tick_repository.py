from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from data_system.models.bot_tick_model import BotTick, Signal
from data_system.repositories.bot_tick.supabase_bot_tick_repository import SupabaseBotTickRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_tick_repository
class TestSupabaseBotTickRepository:
    @pytest.fixture
    def mock_supabase_client(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def sample_tick(self) -> BotTick:
        return BotTick(
            bot_id='test_bot_id',
            run_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            price=Decimal('50000.00'),
            signal=Signal.HOLD,
            balance_base=Decimal('0.001'),
            balance_quote=Decimal('100.00')
        )

    @pytest.fixture
    def mock_response_data(self, sample_tick: BotTick) -> dict:
        ''' Returns data as Supabase would - strings for UUIDs, datetimes, decimals. '''
        return {
            'id': 1,
            'bot_id': sample_tick.bot_id,
            'run_id': str(sample_tick.run_id),
            'timestamp': sample_tick.timestamp.isoformat(),
            'price': str(sample_tick.price),
            'signal': sample_tick.signal.value,
            'balance_base': str(sample_tick.balance_base),
            'balance_quote': str(sample_tick.balance_quote),
            'error': None
        }

    def _set_select_ordered_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().order().execute() '''
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = data

    def _set_insert_response(self, client, data: list) -> None:
        ''' Sets response for: table().insert().execute() '''
        client.table.return_value.insert.return_value.execute.return_value.data = data

    def test_get_by_bot_id_returns_empty_list_when_no_ticks(self, mock_supabase_client):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id('nonexistent_bot')

        # Then
        assert result == []
        mock_supabase_client.table.assert_called_once_with('bot_ticks')

    def test_get_by_bot_id_returns_ticks_when_found(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id(sample_tick.bot_id)

        # Then
        assert len(result) == 1
        assert result[0].bot_id == sample_tick.bot_id

    def test_get_by_bot_id_orders_by_timestamp_descending(self, mock_supabase_client):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        repository.get_by_bot_id('test_bot')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            'timestamp', desc=True
        )

    def test_add_inserts_tick_and_returns_result(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(sample_tick)

        # Then
        assert result.bot_id == sample_tick.bot_id
        mock_supabase_client.table.assert_called_with('bot_ticks')

    def test_add_removes_id_from_record(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        repository.add(sample_tick)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert 'id' not in inserted_record

    def test_add_converts_run_id_to_string(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        repository.add(sample_tick)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['run_id'] == str(sample_tick.run_id)

    def test_add_converts_timestamp_to_iso_format(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        repository.add(sample_tick)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['timestamp'] == sample_tick.timestamp.isoformat()

    def test_add_serialises_decimal_fields_as_strings(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        repository.add(sample_tick)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['price'] == str(sample_tick.price)
        assert inserted_record['balance_base'] == str(sample_tick.balance_base)
        assert inserted_record['balance_quote'] == str(sample_tick.balance_quote)

    def test_add_parses_response_uuid_to_uuid_object(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(sample_tick)

        # Then
        assert isinstance(result.run_id, UUID)
        assert result.run_id == sample_tick.run_id

    def test_add_parses_response_timestamp_to_datetime(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(sample_tick)

        # Then
        assert isinstance(result.timestamp, datetime)
        assert result.timestamp == sample_tick.timestamp

    def test_add_parses_response_decimals_to_decimal_objects(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(sample_tick)

        # Then
        assert isinstance(result.price, Decimal)
        assert isinstance(result.balance_base, Decimal)
        assert isinstance(result.balance_quote, Decimal)
        assert result.price == sample_tick.price
        assert result.balance_base == sample_tick.balance_base
        assert result.balance_quote == sample_tick.balance_quote

    def test_add_preserves_full_decimal_precision_on_round_trip(self, mock_supabase_client):
        # Given — values with 12 decimal places; float conversion would silently corrupt them
        tick = BotTick(
            bot_id='test_bot_id',
            run_id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            price=Decimal('50000.123456789012'),
            signal=Signal.HOLD,
            balance_base=Decimal('0.001234567890'),
            balance_quote=Decimal('100.000000000001'),
        )
        response_data = {
            'id': 1,
            'bot_id': tick.bot_id,
            'run_id': str(tick.run_id),
            'timestamp': tick.timestamp.isoformat(),
            'price': '50000.123456789012',
            'signal': tick.signal.value,
            'balance_base': '0.001234567890',
            'balance_quote': '100.000000000001',
            'error': None,
        }
        self._set_insert_response(mock_supabase_client, [response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(tick)

        # Then — serialised as exact strings without float loss
        inserted_record = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted_record['price'] == '50000.123456789012'
        assert inserted_record['balance_base'] == '0.001234567890'
        assert inserted_record['balance_quote'] == '100.000000000001'
        # And deserialised back to Decimal with full precision
        assert result.price == Decimal('50000.123456789012')
        assert result.balance_base == Decimal('0.001234567890')
        assert result.balance_quote == Decimal('100.000000000001')

    def test_add_parses_response_signal_to_enum(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.add(sample_tick)

        # Then
        assert isinstance(result.signal, Signal)
        assert result.signal == Signal.HOLD

    def test_add_raises_error_when_response_is_empty(self, mock_supabase_client, sample_tick: BotTick):
        # Given
        self._set_insert_response(mock_supabase_client, [])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When / Then
        with pytest.raises(RuntimeError):
            repository.add(sample_tick)

    def test_get_by_bot_id_parses_response_types_correctly(self, mock_supabase_client, sample_tick: BotTick, mock_response_data: dict):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotTickRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id(sample_tick.bot_id)

        # Then
        assert len(result) == 1
        tick = result[0]
        assert isinstance(tick.run_id, UUID)
        assert isinstance(tick.timestamp, datetime)
        assert isinstance(tick.price, Decimal)
        assert isinstance(tick.balance_base, Decimal)
        assert isinstance(tick.balance_quote, Decimal)
        assert isinstance(tick.signal, Signal)
        assert tick.price == sample_tick.price
        assert tick.balance_base == sample_tick.balance_base
        assert tick.balance_quote == sample_tick.balance_quote
