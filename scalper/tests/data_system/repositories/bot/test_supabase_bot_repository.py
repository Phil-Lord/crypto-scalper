import pytest

from data_system.repositories.bot.supabase_bot_repository import SupabaseBotRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_repository
class TestSupabaseBotRepository:
    @pytest.fixture
    def mock_client(self, mocker):
        return mocker.MagicMock()

    def test_get_returns_none_when_bot_not_found(self, mock_client):
        # Given
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        repository = SupabaseBotRepository(mock_client)

        # When
        result = repository.get('nonexistent_bot')

        # Then
        assert result is None
        mock_client.table.assert_called_once_with('bots')
