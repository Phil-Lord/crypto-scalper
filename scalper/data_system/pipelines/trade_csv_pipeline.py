from api import KrakenApiClient
from services import TradesService
from storage.csv import CsvHandler


class TradeCsvPipeline:
    def __init__(self, pair: str, since: int, until: int):
        client = KrakenApiClient()
        self.service = TradesService(client)
        self.storage = CsvHandler(pair)

        self.pair = pair
        self.since = since
        self.until = until

    def update_stored_trades(self):
        raw_trades = self.service.fetch_trades(self.pair, self.since, self.until)
        self.storage.save_trades(raw_trades)
