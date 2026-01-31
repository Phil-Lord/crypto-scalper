import pytest

from utils import get_env_var


@pytest.mark.utils
@pytest.mark.env_vars
class TestGetEnvVar:
    def test_returns_value_from_env_file(self, monkeypatch, tmp_path):
        # Given
        env_file = tmp_path / '.env'
        env_file.write_text('FOO=bar\n')
        monkeypatch.setattr('utils.env_vars.ROOT_DIR', tmp_path)

        # When
        result = get_env_var('FOO')

        # Then
        assert result == 'bar'

    def test_returns_none_for_missing_var(self, monkeypatch, tmp_path):
        # Given
        env_file = tmp_path / '.env'
        env_file.write_text('')
        monkeypatch.setattr('utils.env_vars.ROOT_DIR', tmp_path)

        # When
        result = get_env_var('NONEXISTENT')

        # Then
        assert result is None
