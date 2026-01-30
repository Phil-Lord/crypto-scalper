import pytest

from data_system.clients.supabase_client import SupabaseClient


@pytest.mark.data_system
@pytest.mark.clients
@pytest.mark.supabase_client
class TestSupabaseClient:
    def test_init_creates_client(self, mocker):
        # Given
        mock_create_client = mocker.patch(
            'data_system.clients.supabase_client.create_client'
        )
        mocker.patch(
            'data_system.clients.supabase_client.SupabaseConfig.URL',
            'https://fake.supabase.co'
        )
        mocker.patch(
            'data_system.clients.supabase_client.SupabaseConfig.KEY',
            'fake-api-key'
        )

        # When
        client = SupabaseClient()

        # Then
        mock_create_client.assert_called_once_with(
            'https://fake.supabase.co',
            'fake-api-key'
        )
        assert client._client is mock_create_client.return_value
