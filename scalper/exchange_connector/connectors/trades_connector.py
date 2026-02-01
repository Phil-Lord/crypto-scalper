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
        ''' Raw format: [[price, volume, time, buy/sell, market/limit, misc, trade_id], ...] '''
        return [
            Trade(
                trade_id=int(raw[6]),
                pair=pair,
                price=float(raw[0]),
                volume=float(raw[1]),
                timestamp=float(raw[2]),
                side=str(raw[3]),
                order_type=str(raw[4])
            )
            for raw in raw_trades
        ]
