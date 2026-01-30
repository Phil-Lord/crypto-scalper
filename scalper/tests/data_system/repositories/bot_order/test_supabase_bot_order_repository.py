import pytest

from data_system.repositories.bot_order.supabase_bot_order_repository import SupabaseBotOrderRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_order_repository
class TestSupabaseBotOrderRepository:
    @pytest.fixture
    def mock_client(self, mocker):
        return mocker.MagicMock()

    def test_get_by_bot_id_returns_empty_list_when_no_orders(self, mock_client):
        # Given
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        repository = SupabaseBotOrderRepository(mock_client)

        # When
        result = repository.get_by_bot_id('nonexistent_bot')

        # Then
        assert result == []
        mock_client.table.assert_called_once_with('bot_orders')
