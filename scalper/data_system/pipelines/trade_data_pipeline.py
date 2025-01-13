from api import KrakenApiClient
from services import TradesService


class TradeDataPipeline:
    def __init__(self, pair: str, since: int, until: int):
        client = KrakenApiClient()
        self.service = TradesService(client)

        self.pair = pair
        self.since = since
        self.until = until

    def get_trades(self):
        return self.service.fetch_trades(self.pair, self.since, self.until)
