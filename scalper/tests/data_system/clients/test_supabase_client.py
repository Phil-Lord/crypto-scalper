import pytest

from data_system.clients.supabase_client import SupabaseClient


@pytest.mark.data_system
@pytest.mark.clients
@pytest.mark.supabase_client
class TestSupabaseClient:
    @pytest.fixture
    def mock_supabase_config(self, mocker):
        mocker.patch(
            'data_system.clients.supabase_client.SupabaseConfig.URL',
            'https://fake.supabase.co'
        )
        mocker.patch(
            'data_system.clients.supabase_client.SupabaseConfig.KEY',
            'fake-api-key'
        )

    @pytest.fixture
    def mock_create_client(self, mocker, mock_supabase_config):
        return mocker.patch('data_system.clients.supabase_client.create_client')

    def test_init_creates_client_with_config(self, mock_create_client):
        # When
        client = SupabaseClient()

        # Then
        mock_create_client.assert_called_once_with(
            'https://fake.supabase.co',
            'fake-api-key'
        )
        assert client._client is mock_create_client.return_value

    def test_getattr_delegates_to_underlying_client(self, mock_create_client):
        # Given
        mock_underlying = mock_create_client.return_value
        mock_underlying.table.return_value = 'mock_table_result'
        client = SupabaseClient()

        # When
        result = client.table('test_table')

        # Then
        mock_underlying.table.assert_called_once_with('test_table')
        assert result == 'mock_table_result'

    def test_getattr_delegates_multiple_methods(self, mock_create_client):
        # Given
        mock_underlying = mock_create_client.return_value
        client = SupabaseClient()

        # When
        client.auth
        client.storage

        # Then
        assert mock_underlying.auth is not None
        assert mock_underlying.storage is not None
