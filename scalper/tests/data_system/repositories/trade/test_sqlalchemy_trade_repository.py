from contextlib import contextmanager
from unittest.mock import MagicMock

import pytest

from data_system.clients.sqlalchemy_client import SQLAlchemyClient
from data_system.models.trade_model import Trade
from data_system.repositories.trade.sqlalchemy_trade_repository import SQLAlchemyTradeRepository


@pytest.mark.data_system
@pytest.mark.repositories
@pytest.mark.sqlalchemy_trade_repository
class TestSQLAlchemyTradeRepository:
    @pytest.fixture
    def mock_session(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def mock_client(self, mocker, mock_session):
        client = mocker.MagicMock(spec=SQLAlchemyClient)

        @contextmanager
        def session_context():
            yield mock_session

        client.session = session_context
        return client

    @pytest.fixture
    def sample_trade(self) -> Trade:
        return Trade(
            trade_id=123456789,
            pair='XXBTZGBP',
            price=50000.0,
            volume=0.001,
            timestamp=1704067200.123,
            side='b',
            order_type='m'
        )

    def test_add_with_empty_list_does_nothing(self, mocker):
        # Given
        mock_client = mocker.MagicMock(spec=SQLAlchemyClient)
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.add([])

        # Then
        mock_client.session.assert_not_called()

    def test_add_inserts_trades(self, mock_client, mock_session, sample_trade: Trade, capsys):
        # Given
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.add([sample_trade])

        # Then
        mock_session.execute.assert_called_once()
        captured = capsys.readouterr()
        assert 'Inserting 1 trades for XXBTZGBP' in captured.out

    def test_add_passes_correct_records_to_execute(self, mock_client, mock_session, sample_trade: Trade):
        # Given
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.add([sample_trade])

        # Then
        call_args = mock_session.execute.call_args
        records = call_args[0][1]
        assert len(records) == 1
        assert records[0] == sample_trade.__dict__

    def test_add_handles_multiple_trades(self, mock_client, mock_session):
        # Given
        trades = [
            Trade(
                trade_id=i,
                pair='XXBTZGBP',
                price=50000.0 + i,
                volume=0.001,
                timestamp=1704067200.0 + i,
                side='b',
                order_type='m'
            )
            for i in range(3)
        ]
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.add(trades)

        # Then
        call_args = mock_session.execute.call_args
        records = call_args[0][1]
        assert len(records) == 3
        assert records[0]['trade_id'] == 0
        assert records[1]['trade_id'] == 1
        assert records[2]['trade_id'] == 2

    def test_get_returns_empty_list_when_no_trades(self, mock_client, mock_session):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []
        mock_session.execute.return_value = mock_result
        mock_session.execute.return_value.scalar.return_value = 1704067200.0
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        result = repository.get(pair='XXBTZGBP', start=1704067200.0, end=1704153600.0)

        # Then
        assert result == []

    def test_get_returns_trades(self, mock_client, mock_session, sample_trade: Trade):
        # Given
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            (
                sample_trade.trade_id,
                sample_trade.pair,
                sample_trade.price,
                sample_trade.volume,
                sample_trade.timestamp,
                sample_trade.side,
                sample_trade.order_type
            )
        ]
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        result = repository.get(pair='XXBTZGBP', start=1704067200.0, end=1704153600.0)

        # Then
        assert len(result) == 1
        assert result[0].trade_id == sample_trade.trade_id
        assert result[0].pair == sample_trade.pair

    def test_get_queries_min_timestamp_when_start_is_none(self, mock_client, mock_session):
        # Given
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 1704067200.0
        mock_fetch_result = MagicMock()
        mock_fetch_result.fetchall.return_value = []
        mock_session.execute.side_effect = [
            mock_scalar_result, mock_fetch_result, mock_fetch_result]
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.get(pair='XXBTZGBP', start=None, end=1704153600.0)

        # Then
        assert mock_session.execute.call_count >= 2

    def test_get_queries_max_timestamp_when_end_is_none(self, mock_client, mock_session):
        # Given
        mock_scalar_result = MagicMock()
        mock_scalar_result.scalar.return_value = 1704153600.0
        mock_fetch_result = MagicMock()
        mock_fetch_result.fetchall.return_value = []
        mock_session.execute.side_effect = [mock_scalar_result, mock_fetch_result]
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        repository.get(pair='XXBTZGBP', start=1704067200.0, end=None)

        # Then
        assert mock_session.execute.call_count >= 2

    def test_get_orders_by_timestamp_ascending(self, mock_client, mock_session):
        ''' Verifies trades are returned in chronological order. '''
        # Given
        trade_data = [
            (123, 'XXBTZGBP', 50000.0, 0.001, 1704067200.0, 'b', 'm'),
            (124, 'XXBTZGBP', 50100.0, 0.002, 1704067201.0, 's', 'l'),
            (125, 'XXBTZGBP', 50200.0, 0.003, 1704067202.0, 'b', 'm'),
        ]
        mock_result = MagicMock()
        mock_result.fetchall.return_value = trade_data
        mock_session.execute.return_value = mock_result
        repository = SQLAlchemyTradeRepository(mock_client)

        # When
        result = repository.get(pair='XXBTZGBP', start=1704067200.0, end=1704153600.0)

        # Then
        assert len(result) == 3
        assert result[0].timestamp < result[1].timestamp < result[2].timestamp
