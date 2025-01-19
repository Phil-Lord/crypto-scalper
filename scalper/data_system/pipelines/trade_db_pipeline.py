from api import KrakenApiClient
from services import TradesService
from storage.database import SessionLocal, TradeCRUD


class TradeDbPipeline():
    def __init__(self, pair: str, start: int, end: int):
        client = KrakenApiClient()
        self.service = TradesService(client)
        self.pair = pair
        self.start = start
        self.end = end

    def fetch_and_store_trades(self):
        # Fetch raw trade data from the Kraken Trades API endpoint.
        trades = self.service.fetch_trades(self.pair, self.start, self.end)

        # Frame the insert transaction within a context manager for safe session handling.
        with SessionLocal() as session:
            crud = TradeCRUD(session)
            crud.insert_trades(trades, self.pair)
