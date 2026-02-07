import os

import pytest

from utils import load_env


@pytest.mark.utils
@pytest.mark.env_vars
class TestLoadEnv:
    def test_loads_vars_from_env_file(self, monkeypatch, tmp_path):
        # Given
        env_file = tmp_path / '.env'
        env_file.write_text('FOO=bar\n')
        monkeypatch.setattr('utils.env_vars.ROOT_DIR', tmp_path)
        monkeypatch.delenv('FOO', raising=False)  # Ensure not in actual env

        # When
        load_env()

        # Then
        assert os.getenv('FOO') == 'bar'

    def test_does_not_override_existing_env_vars(self, monkeypatch, tmp_path):
        # Given
        env_file = tmp_path / '.env'
        env_file.write_text('FOO=from_file\n')
        monkeypatch.setattr('utils.env_vars.ROOT_DIR', tmp_path)
        monkeypatch.setenv('FOO', 'from_env')

        # When
        load_env()

        # Then
        assert os.getenv('FOO') == 'from_env'  # Should not override
