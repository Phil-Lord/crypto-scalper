import sys

import pytest


@pytest.mark.data_system
@pytest.mark.config
@pytest.mark.supabase_config
class TestSupabaseConfig:
    def test_config_loads_url_from_env_var(self, mocker):
        ''' Module must be reloaded after patching since class attrs are set at import time. '''
        # Given
        sys.modules.pop('data_system.config.supabase_config', None)
        mocker.patch(
            'os.getenv',
            side_effect=lambda key, default=None: 'https://test.supabase.co' if key == 'SUPABASE_URL' else default
        )

        # When
        from data_system.config.supabase_config import SupabaseConfig

        # Then
        assert SupabaseConfig.URL == 'https://test.supabase.co'

    def test_config_loads_key_from_env_var(self, mocker):
        ''' Module must be reloaded after patching since class attrs are set at import time. '''
        # Given
        sys.modules.pop('data_system.config.supabase_config', None)
        mocker.patch(
            'os.getenv',
            side_effect=lambda key, default=None: 'test-api-key' if key == 'SUPABASE_KEY' else default
        )

        # When
        from data_system.config.supabase_config import SupabaseConfig

        # Then
        assert SupabaseConfig.KEY == 'test-api-key'
