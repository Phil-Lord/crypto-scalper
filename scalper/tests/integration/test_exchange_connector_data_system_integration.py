import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone

from exchange_connector.connectors.trades_connector import TradesConnector
from data_system.clients import SQLAlchemyClient
from data_system.repositories import SQLAlchemyTradeRepository
from data_system.models import Trade


@pytest.mark.integration
@pytest.mark.exchange_connector_data_system_integration
class TestExchangeConnectorDataSystemIntegration:
    '''
    Integration tests for Exchange Connector <-> Data System interaction.

    These tests verify that the full stack works correctly end-to-end:
    - Exchange Connector fetches data from API (mocked)
    - Data System stores the fetched data
    - Data System retrieves the stored data
    - Data integrity is maintained through the round-trip

    Mocks only external boundaries (HTTP requests, database connections).
    All internal layers (connectors, services, repositories, clients) run normally.
    '''

    # ==================== Fixtures ====================

    @pytest.fixture(autouse=True)
    def mock_external_dependencies(self):
        '''Auto-applied fixture that mocks all external dependencies for speed.'''
        # Mock tenacity sleep to prevent retry delays
        with patch('tenacity.nap.sleep'):
            # Mock tqdm progress bar
            mock_tqdm = MagicMock()
            mock_tqdm.__enter__.return_value = mock_tqdm
            mock_tqdm.__exit__.return_value = None
            mock_tqdm.update.return_value = None

            with patch('exchange_connector.services.trades_service.tqdm', return_value=mock_tqdm):
                yield

    @pytest.fixture
    def mock_kraken_trades_response(self):
        '''Mock Kraken API response with realistic trade data.'''
        return {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    ['50000.00000', '0.00100000', 1704067200.123456, 'b', 'm', '', 123456789],
                    ['50001.00000', '0.00200000', 1704067201.234567, 's', 'l', '', 123456790],
                    ['50002.00000', '0.00150000', 1704067202.345678, 'b', 'm', '', 123456791],
                    ['50003.00000', '0.00300000', 1704067203.456789, 's', 'l', '', 123456792],
                    ['50004.00000', '0.00250000', 1704067204.567890, 'b', 'm', '', 123456793],
                ],
                # Set 'last' very high to prevent pagination in all tests
                'last': '9999999999999999999'
            }
        }

    @pytest.fixture
    def mock_empty_trades_response(self):
        '''Mock Kraken API response with no trades.'''
        return {
            'error': [],
            'result': {
                'XXBTZGBP': [],
                'last': '9999999999999999999'
            }
        }

    # ==================== Exchange Connector -> Data System Tests ====================

    def test_fetch_and_store_trades_full_stack(self, mock_kraken_trades_response):
        '''
        Test complete flow: fetch trades from exchange -> store in database.
        Verifies that Trade objects created by connector can be stored by repository.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000  # Nanoseconds
        end = 1704067300000000000

        # Setup Exchange Connector with mocked HTTP
        connector = TradesConnector()

        # Setup Data System with mocked database
        mock_session = MagicMock()
        mock_engine = Mock()

        # When
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            # Mock HTTP response
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            # Fetch trades from exchange (connector transforms to Trade objects)
            trades = connector.fetch(pair, start, end)

            # Store trades in database
            with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
                with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                    mock_session_class = Mock()
                    mock_session_class.return_value = mock_session
                    mock_sessionmaker.return_value = mock_session_class

                    client = SQLAlchemyClient()
                    repository = SQLAlchemyTradeRepository(client)
                    repository.add(trades)

        # Then - Verify trades were fetched and stored correctly
        assert len(trades) == 4  # Service excludes last item with [:-1]
        assert all(isinstance(t, Trade) for t in trades)

        # Verify database insert was called
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args

        # Verify SQL statement
        sql_stmt = str(call_args[0][0])
        assert 'INSERT OR IGNORE INTO trades' in sql_stmt

        # Verify all trades were sent to database
        records = call_args[0][1]
        assert len(records) == 4

        # Verify data transformation from connector to repository
        assert records[0]['trade_id'] == trades[0].trade_id
        assert records[0]['pair'] == pair
        assert records[0]['price'] == 50000.0
        assert records[0]['volume'] == 0.001
        assert records[0]['side'] == 'b'

        assert records[3]['trade_id'] == 123456792
        assert records[3]['price'] == 50003.0

        # Verify transaction committed
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    def test_round_trip_data_integrity(self, mock_kraken_trades_response):
        '''
        Test complete round-trip: fetch from exchange -> store -> retrieve from database.
        Verifies that Trade objects maintain data integrity through the full cycle.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000  # Nanoseconds for connector
        end = 1704067300000000000
        start_seconds = 1704067200.0  # Seconds for repository
        end_seconds = 1704067205.0

        # Setup Exchange Connector
        connector = TradesConnector()

        # Setup Data System
        mock_session = MagicMock()
        mock_engine = Mock()

        # When - Fetch from exchange
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            fetched_trades = connector.fetch(pair, start, end)

        # Store in database
        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(fetched_trades)

                # Mock database response for retrieval
                mock_result = Mock()
                mock_rows = [
                    (t.trade_id, t.pair, t.price, t.volume, t.timestamp, t.side, t.order_type)
                    for t in fetched_trades
                ]
                mock_result.fetchall.return_value = mock_rows
                mock_session.execute.return_value = mock_result

                # Retrieve from database
                retrieved_trades = repository.get(pair, start_seconds, end_seconds)

        # Then - Verify round-trip data integrity
        assert len(retrieved_trades) == len(fetched_trades)

        for original, retrieved in zip(fetched_trades, retrieved_trades):
            assert retrieved.trade_id == original.trade_id
            assert retrieved.pair == original.pair
            assert retrieved.price == original.price
            assert retrieved.volume == original.volume
            assert retrieved.timestamp == original.timestamp
            assert retrieved.side == original.side
            assert retrieved.order_type == original.order_type

    def test_multiple_fetches_and_batch_storage(self, mock_kraken_trades_response):
        '''
        Test storing trades from multiple exchange fetches in a single batch.
        Simulates real-world scenario of aggregating data before storage.
        '''
        # Given
        pair = 'XXBTZGBP'
        connector = TradesConnector()
        all_trades = []

        # When - Multiple fetches from exchange
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            # Simulate multiple time range fetches
            for i in range(3):
                start = 1704067200000000000 + (i * 100000000000)
                end = start + 100000000000
                trades = connector.fetch(pair, start, end)
                all_trades.extend(trades)

        # Store all trades in single batch
        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(all_trades)

        # Then - Verify batch storage
        assert len(all_trades) == 12  # 4 trades per fetch * 3 fetches
        mock_session.execute.assert_called_once()

        records = mock_session.execute.call_args[0][1]
        assert len(records) == 12

        # Verify data from all fetches included
        trade_ids = [r['trade_id'] for r in records]
        assert len(set(trade_ids)) == 4  # Unique trade IDs (same trades fetched 3 times)

    def test_empty_trades_no_storage_operation(self, mock_empty_trades_response):
        '''
        Test that empty trade results from exchange don\'t trigger database operations.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()
        mock_session = MagicMock()
        mock_engine = Mock()

        # When
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_empty_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            trades = connector.fetch(pair, start, end)

            with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
                with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                    mock_session_class = Mock()
                    mock_session_class.return_value = mock_session
                    mock_sessionmaker.return_value = mock_session_class

                    client = SQLAlchemyClient()
                    repository = SQLAlchemyTradeRepository(client)
                    repository.add(trades)

        # Then - Verify no database operations for empty list
        assert len(trades) == 0
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    def test_trade_deduplication_via_composite_key(self, mock_kraken_trades_response):
        '''
        Test that duplicate trades (same trade_id + pair) are handled by database.
        Verifies INSERT OR IGNORE behavior for idempotent storage.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()

        # When - Fetch same data twice
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            first_fetch = connector.fetch(pair, start, end)
            second_fetch = connector.fetch(pair, start, end)

        # Store both batches (simulating duplicate fetches)
        all_trades = first_fetch + second_fetch

        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(all_trades)

        # Then - Verify INSERT OR IGNORE handles duplicates
        assert len(all_trades) == 8  # 4 trades * 2 fetches
        sql_stmt = str(mock_session.execute.call_args[0][0])
        assert 'INSERT OR IGNORE' in sql_stmt  # Duplicate prevention

        records = mock_session.execute.call_args[0][1]
        assert len(records) == 8  # All sent to database, DB handles deduplication

    # ==================== Error Handling Tests ====================

    def test_connector_error_prevents_storage(self):
        '''
        Test that connector errors prevent database operations.
        Verifies error handling before data reaches repository.
        '''
        # Given
        pair = 'INVALIDPAIR'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()
        error_response = {
            'error': ['EQuery:Unknown asset pair'],
            'result': {}
        }

        # When / Then - Connector raises error, storage never attempted
        from exchange_connector.api.exceptions import KrakenApiResponseError

        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = error_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            with pytest.raises(KrakenApiResponseError):
                trades = connector.fetch(pair, start, end)
                # Storage would never be reached

    def test_malformed_trade_data_prevents_storage(self):
        '''
        Test that malformed trade data from exchange prevents storage.
        Verifies connector validation catches issues before repository.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()
        malformed_response = {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    # Missing required fields
                    ['50000.00000', '0.001'],
                    # Valid trade as last item (will be excluded)
                    ['50001.00000', '0.002', 1704067201.234567, 's', 'l', '', 123456790],
                ],
                'last': '9999999999999999999'
            }
        }

        # When / Then - Connector validation fails, storage never attempted
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = malformed_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            with pytest.raises(ValueError) as exc_info:
                trades = connector.fetch(pair, start, end)

            assert 'Failed to parse' in str(
                exc_info.value) or 'Incomplete data' in str(exc_info.value)

    def test_storage_error_after_successful_fetch(self, mock_kraken_trades_response):
        '''
        Test storage errors after successful exchange fetch.
        Verifies error propagation from repository layer.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()

        # When - Successful fetch
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        # Storage fails
        from sqlalchemy.exc import SQLAlchemyError

        mock_session = MagicMock()
        mock_engine = Mock()
        mock_session.execute.side_effect = SQLAlchemyError('Database connection failed')

        # When / Then - Storage error propagates
        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)

                with pytest.raises(SQLAlchemyError) as exc_info:
                    repository.add(trades)

                assert 'Database connection failed' in str(exc_info.value)
                mock_session.rollback.assert_called_once()

    # ==================== Data Consistency Tests ====================

    def test_timestamp_precision_preserved(self, mock_kraken_trades_response):
        '''
        Test that sub-second timestamp precision is preserved through full stack.
        Critical for trades that occur in the same second.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()

        # When - Fetch and store
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(trades)

        # Then - Verify sub-second precision preserved
        records = mock_session.execute.call_args[0][1]

        # Check different timestamps with microsecond precision
        assert records[0]['timestamp'] == 1704067200.123456
        assert records[1]['timestamp'] == 1704067201.234567
        assert records[2]['timestamp'] == 1704067202.345678

        # Verify all timestamps are distinct (no precision loss)
        timestamps = [r['timestamp'] for r in records]
        assert len(timestamps) == len(set(timestamps))

    def test_trade_order_preserved_through_stack(self, mock_kraken_trades_response):
        '''
        Test that trade ordering is preserved from exchange through storage.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()

        # When
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(trades)

        # Then - Verify order preserved
        records = mock_session.execute.call_args[0][1]

        expected_order = [
            (123456789, 50000.0, 1704067200.123456),
            (123456790, 50001.0, 1704067201.234567),
            (123456791, 50002.0, 1704067202.345678),
            (123456792, 50003.0, 1704067203.456789),
        ]

        for i, (expected_id, expected_price, expected_ts) in enumerate(expected_order):
            assert records[i]['trade_id'] == expected_id
            assert records[i]['price'] == expected_price
            assert records[i]['timestamp'] == expected_ts

    def test_all_trade_fields_mapped_correctly(self, mock_kraken_trades_response):
        '''
        Test that all Trade fields are correctly mapped from exchange to database.
        Comprehensive field validation.
        '''
        # Given
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000

        connector = TradesConnector()

        # When
        with patch('requests.get') as mock_get, patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            mock_post.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        mock_session = MagicMock()
        mock_engine = Mock()

        with patch('data_system.clients.sqlalchemy_client.create_engine', return_value=mock_engine):
            with patch('data_system.clients.sqlalchemy_client.sessionmaker') as mock_sessionmaker:
                mock_session_class = Mock()
                mock_session_class.return_value = mock_session
                mock_sessionmaker.return_value = mock_session_class

                client = SQLAlchemyClient()
                repository = SQLAlchemyTradeRepository(client)
                repository.add(trades)

        # Then - Verify all fields present and correct types
        records = mock_session.execute.call_args[0][1]
        first_record = records[0]

        # Check field presence
        assert 'trade_id' in first_record
        assert 'pair' in first_record
        assert 'price' in first_record
        assert 'volume' in first_record
        assert 'timestamp' in first_record
        assert 'side' in first_record
        assert 'order_type' in first_record

        # Check field types
        assert isinstance(first_record['trade_id'], int)
        assert isinstance(first_record['pair'], str)
        assert isinstance(first_record['price'], float)
        assert isinstance(first_record['volume'], float)
        assert isinstance(first_record['timestamp'], float)
        assert isinstance(first_record['side'], str)
        assert isinstance(first_record['order_type'], str)

        # Check field values match expected
        assert first_record['trade_id'] == 123456789
        assert first_record['pair'] == 'XXBTZGBP'
        assert first_record['price'] == 50000.0
        assert first_record['volume'] == 0.001
        assert first_record['side'] == 'b'
        assert first_record['order_type'] == 'm'
