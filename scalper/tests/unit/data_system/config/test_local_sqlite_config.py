import pytest

from data_system.config.local_sqlite_config import LocalSQLiteConfig


@pytest.mark.data_system
@pytest.mark.config
@pytest.mark.local_sqlite_config
class TestLocalSQLiteConfig:
    def test_scalper_db_url_is_sqlite_format(self):
        # When
        url = LocalSQLiteConfig.SCALPER_DB_URL

        # Then
        assert url.startswith('sqlite:///')
        assert 'scalper.db' in url

    def test_local_storage_path_exists(self):
        # When
        path = LocalSQLiteConfig.LOCAL_STORAGE_PATH

        # Then
        assert path is not None
        assert 'local_storage' in str(path)

    def test_local_storage_path_is_under_scalper(self):
        # When
        path = LocalSQLiteConfig.LOCAL_STORAGE_PATH

        # Then
        assert 'scalper' in str(path)
