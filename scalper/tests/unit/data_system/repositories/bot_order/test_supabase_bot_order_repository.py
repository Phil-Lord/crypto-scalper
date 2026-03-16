from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from data_system.models.bot_order_model import BotOrder, OrderStatus, Side
from data_system.repositories.bot_order.supabase_bot_order_repository import SupabaseBotOrderRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_order_repository
class TestSupabaseBotOrderRepository:
    @pytest.fixture
    def mock_supabase_client(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def sample_order(self) -> BotOrder:
        ''' A fully-filled order with all fields populated. '''
        return BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            tick_id=1,
            exchange_order_id='OFLMR7-XXXXX-XXXXXX',
            side=Side.BUY,
            status=OrderStatus.FILLED,
            price=Decimal('50000.00'),
            volume=Decimal('0.001'),
            fee=Decimal('0.50'),
            filled_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def sample_placed_order(self) -> BotOrder:
        ''' A freshly-placed order — fill fields not yet populated. '''
        return BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            exchange_order_id='OFLMR7-XXXXX-XXXXXX',
            side=Side.BUY,
        )

    @pytest.fixture
    def mock_response_data(self, sample_order: BotOrder) -> dict:
        ''' Returns data as Supabase would — strings for UUIDs, datetimes, and decimals. '''
        return {
            'id': str(sample_order.id),
            'bot_id': sample_order.bot_id,
            'run_id': str(sample_order.run_id),
            'tick_id': sample_order.tick_id,
            'exchange_order_id': sample_order.exchange_order_id,
            'side': sample_order.side.value,
            'status': sample_order.status.value,
            'placed_at': sample_order.placed_at.isoformat(),
            'filled_at': sample_order.filled_at.isoformat(),
            'price': str(sample_order.price),
            'volume': str(sample_order.volume),
            'fee': str(sample_order.fee),
        }

    @pytest.fixture
    def mock_placed_response_data(self, sample_placed_order: BotOrder) -> dict:
        ''' Returns data for a PLACED order — fill fields are null. '''
        return {
            'id': str(sample_placed_order.id),
            'bot_id': sample_placed_order.bot_id,
            'run_id': str(sample_placed_order.run_id),
            'tick_id': None,
            'exchange_order_id': sample_placed_order.exchange_order_id,
            'side': sample_placed_order.side.value,
            'status': sample_placed_order.status.value,
            'placed_at': sample_placed_order.placed_at.isoformat(),
            'filled_at': None,
            'price': None,
            'volume': None,
            'fee': None,
        }

    def _set_select_ordered_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().order().execute() '''
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = data

    def _set_select_double_eq_ordered_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().eq().order().execute() '''
        client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.execute.return_value.data = data

    def _set_insert_response(self, client, data: list) -> None:
        ''' Sets response for: table().insert().execute() '''
        client.table.return_value.insert.return_value.execute.return_value.data = data

    def _set_update_response(self, client, data: list) -> None:
        ''' Sets response for: table().update().eq().execute() '''
        client.table.return_value.update.return_value.eq.return_value.execute.return_value.data = data

    # --- add ---

    def test_add_inserts_order_and_returns_result(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert result == sample_order
        mock_supabase_client.table.assert_called_with('bot_orders')

    def test_add_converts_uuids_to_strings(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_order)

        # Then
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['id'] == str(sample_order.id)
        assert inserted['run_id'] == str(sample_order.run_id)

    def test_add_converts_placed_at_to_iso_format(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_order)

        # Then
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['placed_at'] == sample_order.placed_at.isoformat()

    def test_add_converts_filled_at_to_iso_format_when_set(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_order)

        # Then
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['filled_at'] == sample_order.filled_at.isoformat()

    def test_add_serialises_null_fill_fields_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_placed_order)

        # Then
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['filled_at'] is None
        assert inserted['price'] is None
        assert inserted['volume'] is None
        assert inserted['fee'] is None

    def test_add_serialises_decimal_fields_as_strings(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_order)

        # Then
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['price'] == str(sample_order.price)
        assert inserted['volume'] == str(sample_order.volume)
        assert inserted['fee'] == str(sample_order.fee)

    def test_add_parses_response_uuids_to_uuid_objects(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.id, UUID)
        assert isinstance(result.run_id, UUID)
        assert result.id == sample_order.id
        assert result.run_id == sample_order.run_id

    def test_add_parses_response_placed_at_to_datetime(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.placed_at, datetime)
        assert result.placed_at == sample_order.placed_at

    def test_add_parses_response_filled_at_to_datetime(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.filled_at, datetime)
        assert result.filled_at == sample_order.filled_at

    def test_add_parses_null_filled_at_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_placed_order)

        # Then
        assert result.filled_at is None

    def test_add_parses_response_decimals_to_decimal_objects(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.price, Decimal)
        assert isinstance(result.volume, Decimal)
        assert isinstance(result.fee, Decimal)
        assert result.price == sample_order.price
        assert result.volume == sample_order.volume
        assert result.fee == sample_order.fee

    def test_add_parses_null_decimals_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_placed_order)

        # Then
        assert result.price is None
        assert result.volume is None
        assert result.fee is None

    def test_add_preserves_full_decimal_precision_on_round_trip(self, mock_supabase_client):
        # Given — values with 12 decimal places; float conversion would silently corrupt them
        order = BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            tick_id=1,
            exchange_order_id='OFLMR7-XXXXX-XXXXXX',
            side=Side.BUY,
            status=OrderStatus.FILLED,
            price=Decimal('50000.123456789012'),
            volume=Decimal('0.001234567890'),
            fee=Decimal('0.500000000001'),
            filled_at=datetime.now(timezone.utc),
        )
        response_data = {
            'id': str(order.id),
            'bot_id': order.bot_id,
            'run_id': str(order.run_id),
            'tick_id': order.tick_id,
            'exchange_order_id': order.exchange_order_id,
            'side': order.side.value,
            'status': order.status.value,
            'placed_at': order.placed_at.isoformat(),
            'filled_at': order.filled_at.isoformat(),
            'price': '50000.123456789012',
            'volume': '0.001234567890',
            'fee': '0.500000000001',
        }
        self._set_insert_response(mock_supabase_client, [response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(order)

        # Then — serialised as exact strings without float loss
        inserted = mock_supabase_client.table.return_value.insert.call_args[0][0]
        assert inserted['price'] == '50000.123456789012'
        assert inserted['volume'] == '0.001234567890'
        assert inserted['fee'] == '0.500000000001'
        # And deserialised back to Decimal with full precision
        assert result.price == Decimal('50000.123456789012')
        assert result.volume == Decimal('0.001234567890')
        assert result.fee == Decimal('0.500000000001')

    def test_add_parses_response_enums(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.side, Side)
        assert isinstance(result.status, OrderStatus)
        assert result.side == Side.BUY
        assert result.status == OrderStatus.FILLED

    def test_add_raises_error_when_response_is_empty(self, mock_supabase_client, sample_order: BotOrder):
        # Given
        self._set_insert_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When / Then
        with pytest.raises(RuntimeError):
            repository.add(sample_order)

    # --- update ---

    def test_update_returns_updated_order(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert result == sample_order
        mock_supabase_client.table.assert_called_with('bot_orders')

    def test_update_filters_by_order_id(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.update(sample_order)

        # Then
        mock_supabase_client.table.return_value.update.return_value.eq.assert_called_once_with(
            'id', str(sample_order.id)
        )

    def test_update_payload_contains_only_mutable_fields(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.update(sample_order)

        # Then — identity fields must not be sent; only mutable fields are included
        sent = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert set(sent.keys()) == {'status', 'tick_id', 'filled_at', 'price', 'volume', 'fee'}

    def test_update_converts_filled_at_to_iso_format_when_set(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.update(sample_order)

        # Then
        sent = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert sent['filled_at'] == sample_order.filled_at.isoformat()

    def test_update_serialises_null_fill_fields_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.update(sample_placed_order)

        # Then
        sent = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert sent['filled_at'] is None
        assert sent['price'] is None
        assert sent['volume'] is None
        assert sent['fee'] is None

    def test_update_serialises_decimal_fields_as_strings(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.update(sample_order)

        # Then
        sent = mock_supabase_client.table.return_value.update.call_args[0][0]
        assert sent['price'] == str(sample_order.price)
        assert sent['volume'] == str(sample_order.volume)
        assert sent['fee'] == str(sample_order.fee)

    def test_update_parses_response_uuids_to_uuid_objects(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert isinstance(result.id, UUID)
        assert isinstance(result.run_id, UUID)
        assert result.id == sample_order.id
        assert result.run_id == sample_order.run_id

    def test_update_parses_response_placed_at_to_datetime(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert isinstance(result.placed_at, datetime)
        assert result.placed_at == sample_order.placed_at

    def test_update_parses_response_filled_at_to_datetime(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert isinstance(result.filled_at, datetime)
        assert result.filled_at == sample_order.filled_at

    def test_update_parses_null_filled_at_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_placed_order)

        # Then
        assert result.filled_at is None

    def test_update_parses_response_decimals_to_decimal_objects(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert isinstance(result.price, Decimal)
        assert isinstance(result.volume, Decimal)
        assert isinstance(result.fee, Decimal)
        assert result.price == sample_order.price
        assert result.volume == sample_order.volume
        assert result.fee == sample_order.fee

    def test_update_parses_null_decimals_as_none(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_placed_order)

        # Then
        assert result.price is None
        assert result.volume is None
        assert result.fee is None

    def test_update_parses_response_enums(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_update_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.update(sample_order)

        # Then
        assert isinstance(result.side, Side)
        assert isinstance(result.status, OrderStatus)
        assert result.side == Side.BUY
        assert result.status == OrderStatus.FILLED

    def test_update_raises_error_when_order_not_found(self, mock_supabase_client, sample_order: BotOrder):
        # Given
        self._set_update_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When / Then
        with pytest.raises(ValueError):
            repository.update(sample_order)

    # --- get_by_bot_id ---

    def test_get_by_bot_id_returns_empty_list_when_no_orders(self, mock_supabase_client):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id('nonexistent_bot')

        # Then
        assert result == []
        mock_supabase_client.table.assert_called_once_with('bot_orders')

    def test_get_by_bot_id_returns_orders_when_found(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id(sample_order.bot_id)

        # Then
        assert len(result) == 1
        assert result[0] == sample_order
        mock_supabase_client.table.assert_called_once_with('bot_orders')

    def test_get_by_bot_id_orders_by_placed_at_descending(self, mock_supabase_client):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.get_by_bot_id('test_bot')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            'placed_at', desc=True
        )

    def test_get_by_bot_id_parses_response_types_correctly(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id(sample_order.bot_id)

        # Then
        assert len(result) == 1
        order = result[0]
        assert isinstance(order.id, UUID)
        assert isinstance(order.run_id, UUID)
        assert isinstance(order.placed_at, datetime)
        assert isinstance(order.filled_at, datetime)
        assert isinstance(order.price, Decimal)
        assert isinstance(order.volume, Decimal)
        assert isinstance(order.fee, Decimal)
        assert order.price == sample_order.price
        assert order.volume == sample_order.volume
        assert order.fee == sample_order.fee
        assert isinstance(order.side, Side)
        assert isinstance(order.status, OrderStatus)

    def test_get_by_bot_id_parses_null_fill_fields(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_by_bot_id(sample_placed_order.bot_id)

        # Then
        assert len(result) == 1
        order = result[0]
        assert order.filled_at is None
        assert order.price is None
        assert order.volume is None
        assert order.fee is None
        assert order.tick_id is None
        assert order.status == OrderStatus.PLACED

    # --- get_placed_by_bot_id ---

    def test_get_placed_by_bot_id_returns_empty_list_when_no_orders(self, mock_supabase_client):
        # Given
        self._set_select_double_eq_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_placed_by_bot_id('nonexistent_bot')

        # Then
        assert result == []
        mock_supabase_client.table.assert_called_once_with('bot_orders')

    def test_get_placed_by_bot_id_returns_placed_orders_when_found(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_select_double_eq_ordered_response(
            mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_placed_by_bot_id(sample_placed_order.bot_id)

        # Then
        assert len(result) == 1
        assert result[0] == sample_placed_order

    def test_get_placed_by_bot_id_filters_by_bot_id(self, mock_supabase_client):
        # Given
        self._set_select_double_eq_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.get_placed_by_bot_id('btc_1m_001')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.assert_called_once_with(
            'bot_id', 'btc_1m_001'
        )

    def test_get_placed_by_bot_id_filters_by_placed_status(self, mock_supabase_client):
        # Given
        self._set_select_double_eq_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.get_placed_by_bot_id('btc_1m_001')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.assert_called_once_with(
            'status', OrderStatus.PLACED.value
        )

    def test_get_placed_by_bot_id_orders_by_placed_at_descending(self, mock_supabase_client):
        # Given
        self._set_select_double_eq_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.get_placed_by_bot_id('btc_1m_001')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.eq.return_value.order.assert_called_once_with(
            'placed_at', desc=True
        )

    def test_get_placed_by_bot_id_parses_response_types_correctly(self, mock_supabase_client, sample_placed_order: BotOrder, mock_placed_response_data: dict):
        # Given
        self._set_select_double_eq_ordered_response(
            mock_supabase_client, [mock_placed_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.get_placed_by_bot_id(sample_placed_order.bot_id)

        # Then
        assert len(result) == 1
        order = result[0]
        assert isinstance(order.id, UUID)
        assert isinstance(order.run_id, UUID)
        assert isinstance(order.placed_at, datetime)
        assert isinstance(order.side, Side)
        assert isinstance(order.status, OrderStatus)
        assert order.status == OrderStatus.PLACED
        assert order.filled_at is None
        assert order.price is None
        assert order.volume is None
        assert order.fee is None
