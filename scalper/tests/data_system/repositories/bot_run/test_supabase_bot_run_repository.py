import pytest

from data_system.repositories.bot_run.supabase_bot_run_repository import SupabaseBotRunRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.supabase_bot_run_repository
class TestSupabaseBotRunRepository:
    @pytest.fixture
    def mock_client(self, mocker):
        return mocker.MagicMock()

    def test_get_returns_none_when_run_not_found(self, mock_client):
        # Given
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        repository = SupabaseBotRunRepository(mock_client)

        # When
        result = repository.get('nonexistent_run_id')

        # Then
        assert result is None
        mock_client.table.assert_called_once_with('bot_runs')
