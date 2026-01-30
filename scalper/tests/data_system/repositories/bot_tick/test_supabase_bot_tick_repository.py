import pytest

from data_system.repositories.bot_tick.supabase_bot_tick_repository import SupabaseBotTickRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_tick_repository
class TestSupabaseBotTickRepository:
    @pytest.fixture
    def mock_client(self, mocker):
        return mocker.MagicMock()

    def test_get_by_bot_id_returns_empty_list_when_no_ticks(self, mock_client):
        # Given
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
        repository = SupabaseBotTickRepository(mock_client)

        # When
        result = repository.get_by_bot_id('nonexistent_bot')

        # Then
        assert result == []
        mock_client.table.assert_called_once_with('bot_ticks')
