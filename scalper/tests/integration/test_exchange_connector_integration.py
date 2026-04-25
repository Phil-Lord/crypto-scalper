from decimal import Decimal

import pytest
from unittest.mock import Mock, patch

from exchange_connector.api.exceptions import KrakenApiResponseError
from exchange_connector.connectors.ticker_connector import TickerConnector
from exchange_connector.connectors.trades_connector import TradesConnector
from exchange_connector.connectors.asset_pairs_connector import AssetPairsConnector
from exchange_connector.connectors.query_orders_connector import QueryOrdersConnector
from exchange_connector.models.query_order_result import QueryOrderResult, QueryOrderStatus
from data_system.models.trade_model import Trade


PATCH_HEADERS = 'exchange_connector.api.kraken_api_client.get_headers'
MOCK_HEADERS = {'API-Key': 'test', 'API-Sign': 'test'}


@pytest.mark.integration
@pytest.mark.exchange_connector_integration
class TestExchangeConnectorIntegration:
    '''
    Integration tests for Exchange Connector module.

    These tests verify that the connector -> service -> client stack works correctly
    by mocking only the HTTP boundary (requests library) and time.sleep(), covering:
    - Layer integration (connector -> service -> client)
    - Domain transformation (raw API responses -> domain objects)
    - Error propagation through layers
    - Parameter handling and validation
    '''

    @pytest.fixture
    def mock_kraken_ticker_response(self):
        return {
            'error': [],
            'result': {
                'XXBTZGBP': {
                    'a': ['50000.00000', '1', '1.000'],
                    'b': ['49999.00000', '2', '2.000'],
                    'c': ['50000.50000', '0.00100000'],
                    'v': ['100.12345678', '200.23456789'],
                    'p': ['49500.00000', '49600.00000'],
                    't': [1000, 2000],
                    'l': ['49000.00000', '48900.00000'],
                    'h': ['51000.00000', '51100.00000'],
                    'o': '49800.00000',
                }
            }
        }

    @pytest.fixture
    def mock_kraken_trades_response(self):
        return {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    ['50000.00000', '0.00100000', 1704067200.123456, 'b', 'm', '', 123456789],
                    ['50001.00000', '0.00200000', 1704067201.234567, 's', 'l', '', 123456790],
                    ['50002.00000', '0.00150000', 1704067202.345678, 'b', 'm', '', 123456791],
                ],
                'last': '1704067400000000000'
            }
        }

    @pytest.fixture
    def mock_kraken_asset_pairs_response(self):
        return {
            'error': [],
            'result': {
                'XXBTZGBP': {
                    'altname': 'BTCGBP',
                    'wsname': 'BTC/GBP',
                    'aclass_base': 'currency',
                    'base': 'XXBT',
                    'aclass_quote': 'currency',
                    'quote': 'ZGBP',
                    'lot': 'unit',
                    'pair_decimals': 1,
                    'lot_decimals': 8,
                    'lot_multiplier': 1,
                    'leverage_buy': [2, 3, 4, 5],
                    'leverage_sell': [2, 3, 4, 5],
                    'fees': [[0, 0.26], [50000, 0.24]],
                    'fees_maker': [[0, 0.16], [50000, 0.14]],
                    'fee_volume_currency': 'ZUSD',
                    'margin_call': 80,
                    'margin_stop': 40,
                }
            }
        }

    def test_ticker_connector_full_stack_integration(self, mock_kraken_ticker_response):
        # Given
        connector = TickerConnector()
        pair = 'XXBTZGBP'

        # When
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_ticker_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            result = connector.fetch(pair)

        # Then
        assert result == mock_kraken_ticker_response['result'][pair]

        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert 'Ticker' in call_args[1]['url']
        assert call_args[1]['params']['pair'] == pair

    def test_trades_connector_domain_transformation_integration(self, mock_kraken_trades_response):
        # Given
        connector = TradesConnector()
        pair = 'XXBTZGBP'
        start = 1704067200000000000  # Nanoseconds
        end = 1704067300000000000

        # When
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        # Then
        assert trades is not None
        assert isinstance(trades, list)
        assert len(trades) == 2  # Service excludes last item with [:-1]

        first_trade = trades[0]
        assert isinstance(first_trade, Trade)
        assert first_trade.pair == pair
        assert first_trade.trade_id == 123456789
        assert first_trade.price == 50000.0
        assert first_trade.volume == 0.001
        assert first_trade.timestamp == 1704067200.123456
        assert first_trade.side == 'b'
        assert first_trade.order_type == 'm'

        second_trade = trades[1]
        assert second_trade.trade_id == 123456790
        assert second_trade.price == 50001.0
        assert second_trade.side == 's'
        assert second_trade.order_type == 'l'

    def test_asset_pairs_connector_data_extraction(self, mock_kraken_asset_pairs_response):
        # Given
        connector = AssetPairsConnector()
        pair = 'XXBTZGBP'

        # When
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_asset_pairs_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            result = connector.fetch(pair)

        # Then
        assert result is not None
        assert isinstance(result, dict)
        assert 'XXBTZGBP' in result

        pair_info = result['XXBTZGBP']
        assert pair_info['altname'] == 'BTCGBP'
        assert pair_info['wsname'] == 'BTC/GBP'
        assert pair_info['base'] == 'XXBT'
        assert pair_info['quote'] == 'ZGBP'
        assert pair_info['pair_decimals'] == 1
        assert pair_info['lot_decimals'] == 8

    def test_trades_connector_with_time_range_parameters(self, mock_kraken_trades_response):
        # Given
        connector = TradesConnector()
        pair = 'XXBTZGBP'
        start = 1704067200000000000  # Nanoseconds
        end = 1704067300000000000

        # When
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_trades_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            trades = connector.fetch(pair, start, end)

        # Then
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert 'since' in call_args[1]['params']  # Service converts to 'since'
        assert len(trades) == 2  # Service excludes last item with [:-1]

    def test_multiple_connectors_work_independently(
        self,
        mock_kraken_ticker_response,
        mock_kraken_trades_response,
        mock_kraken_asset_pairs_response
    ):
        # Given
        ticker_connector = TickerConnector()
        trades_connector = TradesConnector()
        asset_pairs_connector = AssetPairsConnector()
        pair = 'XXBTZGBP'

        # When
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            def mock_response_factory(*args, **kwargs):
                mock_response = Mock()
                mock_response.raise_for_status.return_value = None

                # Setup mock to return different responses based on endpoint
                if 'Ticker' in kwargs['url']:
                    mock_response.json.return_value = mock_kraken_ticker_response
                elif 'Trades' in kwargs['url']:
                    mock_response.json.return_value = mock_kraken_trades_response
                elif 'AssetPairs' in kwargs['url']:
                    mock_response.json.return_value = mock_kraken_asset_pairs_response

                return mock_response

            mock_request.side_effect = mock_response_factory

            start = 1704067200000000000
            end = 1704067300000000000

            ticker_data = ticker_connector.fetch(pair)
            trades_data = trades_connector.fetch(pair, start, end)
            asset_info = asset_pairs_connector.fetch(pair)

        # Then - All connectors work correctly
        assert ticker_data is not None
        assert 'a' in ticker_data

        assert trades_data is not None and len(trades_data) == 2  # Service excludes last item
        assert all(isinstance(t, Trade) for t in trades_data)

        assert asset_info is not None
        assert 'XXBTZGBP' in asset_info
        assert asset_info['XXBTZGBP']['altname'] == 'BTCGBP'

        # Verify all made requests
        assert mock_request.call_count == 3

    def test_error_propagation_through_stack(self):
        # Given
        connector = TickerConnector()
        pair = 'INVALIDPAIR'
        error_response = {
            'error': ['EQuery:Unknown asset pair'],
            'result': {}
        }

        # When / Then - Verify errors propagate through connector -> service -> client
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = error_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            with pytest.raises(KrakenApiResponseError) as exc_info:
                connector.fetch(pair)
            assert 'EQuery:Unknown asset pair' in str(exc_info.value)

    def test_validation_errors_in_domain_transformation(self):
        # Given
        connector = TradesConnector()
        pair = 'XXBTZGBP'
        start = 1704067200000000000
        end = 1704067300000000000
        invalid_trade_response = {
            'error': [],
            'result': {
                'XXBTZGBP': [
                    # Invalid trade data - missing fields (will be included because it's not last)
                    ['50000.00000', '0.001'],
                    # Valid trade as last item (will be excluded by service [:-1])
                    ['50001.00000', '0.002', 1704067201.234567, 's', 'l', '', 123456790],
                ],
                # 'last' must be > end to prevent pagination loop
                'last': '1704067400000000000'
            }
        }

        # When / Then
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = invalid_trade_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response

            with pytest.raises(ValueError) as exc_info:
                connector.fetch(pair, start, end)

            # Verify error indicates transformation failure
            assert 'Failed to parse' in str(
                exc_info.value) or 'Trade data incomplete' in str(exc_info.value)

    # ─── QueryOrdersConnector — connector → service → client integration ───
    #
    # QueryOrders is a private POST endpoint, so the auth header builder is
    # patched to bypass the KRAKEN_TRADING_API_KEY/SECRET requirement; the
    # connector → service → client → signing path otherwise runs unmocked.

    @pytest.fixture
    def mock_kraken_query_orders_response(self):
        return {
            'error': [],
            'result': {
                'OABCDE-FGHIJ-KLMNOP': {
                    'status': 'closed',
                    'price': '49750.00',
                    'vol_exec': '0.50251256',
                    'fee': '6.45',
                },
                'OQRSTU-VWXYZ-012345': {
                    'status': 'open',
                    'price': '0.00',
                    'vol_exec': '0.00',
                    'fee': '0.00',
                },
                'OFAILD-ORDER-CANCEL': {
                    'status': 'canceled',
                    'price': '0.00',
                    'vol_exec': '0.00',
                    'fee': '0.00',
                },
            },
        }

    @pytest.mark.query_orders_connector
    def test_query_orders_connector_full_stack_integration(
            self, mock_kraken_query_orders_response,
    ):
        # Given
        connector = QueryOrdersConnector()
        txids = [
            'OABCDE-FGHIJ-KLMNOP',
            'OQRSTU-VWXYZ-012345',
            'OFAILD-ORDER-CANCEL',
        ]

        # When
        with (
            patch('time.sleep'),
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.post') as mock_post,
        ):
            mock_response = Mock()
            mock_response.json.return_value = mock_kraken_query_orders_response
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            results = connector.fetch(txids)

        # Then — domain transformation produced QueryOrderResult per txid
        assert len(results) == 3
        assert all(isinstance(r, QueryOrderResult) for r in results)

        results_by_txid = {r.txid: r for r in results}

        filled = results_by_txid['OABCDE-FGHIJ-KLMNOP']
        assert filled.status == QueryOrderStatus.CLOSED
        assert filled.price == Decimal('49750.00')
        assert filled.volume == Decimal('0.50251256')
        assert filled.fee == Decimal('6.45')

        open_order = results_by_txid['OQRSTU-VWXYZ-012345']
        assert open_order.status == QueryOrderStatus.OPEN
        assert open_order.price == Decimal('0.00')
        assert open_order.volume == Decimal('0.00')

        cancelled = results_by_txid['OFAILD-ORDER-CANCEL']
        assert cancelled.status == QueryOrderStatus.CANCELED

        # Then — single POST to the QueryOrders endpoint with comma-joined txids
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert mock_post.call_args.args[0].endswith('/0/private/QueryOrders')
        assert call_kwargs['data']['txid'] == ','.join(txids)
        assert 'nonce' in call_kwargs['data']
        assert call_kwargs['headers'] == MOCK_HEADERS

    @pytest.mark.query_orders_connector
    def test_query_orders_connector_returns_empty_for_no_txids(self):
        # Given
        connector = QueryOrdersConnector()

        # When — no HTTP call should be made when there are no txids to query
        with patch('requests.post') as mock_post:
            results = connector.fetch([])

        # Then
        assert results == []
        mock_post.assert_not_called()

    @pytest.mark.query_orders_connector
    def test_query_orders_connector_propagates_kraken_api_error(self):
        # Given
        connector = QueryOrdersConnector()
        error_response = {'error': ['EOrder:Unknown order'], 'result': {}}

        # When / Then — error propagates client → service → connector
        with (
            patch('time.sleep'),
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.post') as mock_post,
        ):
            mock_response = Mock()
            mock_response.json.return_value = error_response
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            with pytest.raises(KrakenApiResponseError) as exc_info:
                connector.fetch(['OUNKNW-ORDER-ID000'])
            assert 'EOrder:Unknown order' in str(exc_info.value)

    @pytest.mark.query_orders_connector
    def test_query_orders_connector_raises_on_malformed_response(self):
        # Given — order entry missing the required 'price' field
        connector = QueryOrdersConnector()
        malformed_response = {
            'error': [],
            'result': {
                'OABCDE-FGHIJ-KLMNOP': {
                    'status': 'closed',
                    'vol_exec': '0.5',
                    'fee': '1.0',
                },
            },
        }

        # When / Then
        with (
            patch('time.sleep'),
            patch(PATCH_HEADERS, return_value=MOCK_HEADERS),
            patch('requests.post') as mock_post,
        ):
            mock_response = Mock()
            mock_response.json.return_value = malformed_response
            mock_response.raise_for_status.return_value = None
            mock_post.return_value = mock_response

            with pytest.raises(ValueError, match='Failed to parse order result'):
                connector.fetch(['OABCDE-FGHIJ-KLMNOP'])
