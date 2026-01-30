import pytest

from data_system.clients.sqlalchemy_client import SQLAlchemyClient


@pytest.mark.data_system
@pytest.mark.clients
@pytest.mark.sqlalchemy_client
class TestSQLAlchemyClient:
    def test_init_creates_engine_with_custom_url(self):
        # Given
        test_url = 'sqlite:///:memory:'

        # When
        client = SQLAlchemyClient(url=test_url)

        # Then
        assert client.engine is not None
        assert str(client.engine.url) == test_url
