from api import KrakenApiClient
from services import TradesService
from storage.database import SessionLocal, TradeCRUD


class TradeDbPipeline():
    def __init__(self, pair: str, start: int, end: int):
        client = KrakenApiClient()
        self.service = TradesService(client)
        self.session = SessionLocal()
        self.crud = TradeCRUD(self.session)

        self.pair = pair
        self.start = start
        self.end = end

    def fetch_and_store_trades(self):
        trades = self.service.fetch_trades(self.pair, self.start, self.end)
        self.crud.insert_trades(trades, self.pair)
