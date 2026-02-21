import pytest

from data_system.config.supabase_config import SupabaseConfig


@pytest.mark.data_system
@pytest.mark.config
@pytest.mark.supabase_config
class TestSupabaseConfig:
    def test_config_loads_url_from_env_var(self, mocker):
        # Given
        mocker.patch.dict('os.environ', {'SUPABASE_URL': 'https://test.supabase.co'})

        # When / Then
        assert SupabaseConfig.URL == 'https://test.supabase.co'

    def test_config_loads_key_from_env_var(self, mocker):
        # Given
        mocker.patch.dict('os.environ', {'SUPABASE_KEY': 'test-api-key'})

        # When / Then
        assert SupabaseConfig.KEY == 'test-api-key'
