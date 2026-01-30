import pytest

from data_system.config.supabase_config import SupabaseConfig


@pytest.mark.data_system
@pytest.mark.config
@pytest.mark.supabase_config
class TestSupabaseConfig:
    def test_config_attributes_exist(self, mocker):
        # Given - mock environment variable retrieval to avoid exposing real keys
        mocker.patch('data_system.config.supabase_config.get_env_var', return_value='mock-value')

        # When - reimport to apply mock
        import importlib
        import data_system.config.supabase_config as config_module
        importlib.reload(config_module)

        # Then
        assert hasattr(config_module.SupabaseConfig, 'URL')
        assert hasattr(config_module.SupabaseConfig, 'KEY')
