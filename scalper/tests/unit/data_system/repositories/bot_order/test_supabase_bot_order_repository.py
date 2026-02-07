from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from data_system.models.bot_order_model import BotOrder, Side
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
        return BotOrder(
            bot_id='btc_1m_001',
            run_id=uuid4(),
            tick_id=1,
            side=Side.BUY,
            price=Decimal('50000.00'),
            volume=Decimal('0.001'),
            fee=Decimal('0.50'),
            executed_at=datetime.now(timezone.utc)
        )

    @pytest.fixture
    def mock_response_data(self, sample_order: BotOrder) -> dict:
        ''' Returns data as Supabase would - strings for UUIDs, datetimes, decimals. '''
        return {
            'id': str(sample_order.id),
            'bot_id': sample_order.bot_id,
            'run_id': str(sample_order.run_id),
            'tick_id': sample_order.tick_id,
            'side': sample_order.side.value,
            'price': str(sample_order.price),
            'volume': str(sample_order.volume),
            'fee': str(sample_order.fee),
            'executed_at': sample_order.executed_at.isoformat()
        }

    def _set_select_ordered_response(self, client, data: list) -> None:
        ''' Sets response for: table().select().eq().order().execute() '''
        client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = data

    def _set_insert_response(self, client, data: list) -> None:
        ''' Sets response for: table().insert().execute() '''
        client.table.return_value.insert.return_value.execute.return_value.data = data

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

    def test_get_by_bot_id_orders_by_executed_at_descending(self, mock_supabase_client):
        # Given
        self._set_select_ordered_response(mock_supabase_client, [])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.get_by_bot_id('test_bot')

        # Then
        mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.assert_called_once_with(
            'executed_at', desc=True
        )

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
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['id'] == str(sample_order.id)
        assert inserted_record['run_id'] == str(sample_order.run_id)

    def test_add_converts_executed_at_to_iso_format(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        repository.add(sample_order)

        # Then
        insert_call = mock_supabase_client.table.return_value.insert
        inserted_record = insert_call.call_args[0][0]
        assert inserted_record['executed_at'] == sample_order.executed_at.isoformat()

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

    def test_add_parses_response_executed_at_to_datetime(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.executed_at, datetime)
        assert result.executed_at == sample_order.executed_at

    def test_add_parses_response_decimals_to_decimal_objects(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.price, Decimal)
        assert isinstance(result.fee, Decimal)
        assert result.price == sample_order.price
        assert result.fee == sample_order.fee

    def test_add_parses_response_side_to_enum(self, mock_supabase_client, sample_order: BotOrder, mock_response_data: dict):
        # Given
        self._set_insert_response(mock_supabase_client, [mock_response_data])
        repository = SupabaseBotOrderRepository(mock_supabase_client)

        # When
        result = repository.add(sample_order)

        # Then
        assert isinstance(result.side, Side)
        assert result.side == Side.BUY

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
        assert isinstance(order.executed_at, datetime)
        assert isinstance(order.price, Decimal)
        assert isinstance(order.fee, Decimal)
        assert isinstance(order.side, Side)
