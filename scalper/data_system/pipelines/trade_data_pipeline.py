from api import KrakenApiClient
from services import TradesService
from storage import CsvHandler
from utils import format_trades


class TradeDataPipeline:
    def __init__(self, pair: str, since: int, until: int):
        client = KrakenApiClient()
        self.service = TradesService(client)
        self.storage = CsvHandler(pair)

        self.pair = pair
        self.since = since
        self.until = until

    def update_stored_trades(self):
        trades_raw = self.service.fetch_trades(self.pair, self.since, self.until)
        trades_df = format_trades(trades_raw)
        self.storage.save_trades(trades_df)
