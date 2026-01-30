import pytest

from data_system.clients.sqlalchemy_client import SQLAlchemyClient
from data_system.repositories.trade.sqlalchemy_trade_repository import SQLAlchemyTradeRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.sqlalchemy_trade_repository
class TestSQLAlchemyTradeRepository:
    @pytest.fixture
    def mock_client(self, mocker):
        return mocker.MagicMock(spec=SQLAlchemyClient)

    def test_add_with_empty_list_does_nothing(self, mock_client):
        # Given
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.add([])

        # Then
        mock_client.session.assert_not_called()
