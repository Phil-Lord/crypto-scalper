from .base_connectors import FetchConnector
from data_system import Trade
from exchange_connector.api import KrakenApiClient
from exchange_connector.services import TradesService


class TradesConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = TradesService(self.client)

    def fetch(self, pair: str, start: int, end: int) -> list[Trade]:
        '''
        Fetch raw trades from Kraken API and return as Trade domain objects.

        :param pair: Trading pair in Kraken format, e.g., 'XXBTZGBP'.
        :param start: Start timestamp in nanoseconds.
        :param end: End timestamp in nanoseconds.
        :return: List of Trade objects.
        '''
        raw_trades = self.service.fetch_trades(pair, start, end)
        return self._to_domain(raw_trades, pair)

    def _to_domain(self, raw_trades: list[list], pair: str) -> list[Trade]:
        '''
        Convert raw Kraken trade arrays to Trade domain objects.

        :param raw_trades: List of raw trade arrays from Kraken API.
        :param pair: Trading pair identifier.
        :return: List of Trade domain objects.
        :raises ValueError: If trade data is malformed.
        '''
        trades = []
        for raw in raw_trades:
            try:
                if len(raw) < 7:
                    raise ValueError(f'Trade data incomplete: expected 7 fields, got {len(raw)}')

                trades.append(Trade(
                    trade_id=int(raw[6]),
                    pair=pair,
                    price=float(raw[0]),
                    volume=float(raw[1]),
                    timestamp=float(raw[2]),
                    side=str(raw[3]),
                    order_type=str(raw[4])
                ))
            except (ValueError, IndexError, TypeError) as e:
                raise ValueError(f'Failed to parse trade data: {raw}. Error: {e}')

        return trades
