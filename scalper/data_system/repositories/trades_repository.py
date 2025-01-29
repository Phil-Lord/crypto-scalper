from .base_repository import Repository
from data_system.database import SessionLocal, TradeCRUD, Trade


class TradesRepository(Repository):
    def add(self, trades: list[list[any]], pair: str) -> None:
        '''
        Insert a list of trades for a certain pair in their raw format from the Kraken API.
        '''
        with SessionLocal() as session:
            crud = TradeCRUD(session)
            crud.add_trades(trades, pair)

    def get(self, pair: str, start: int, end: int) -> list[Trade]:
        '''
        Fetch trades for a certain pair between a start and end date.
        '''
        with SessionLocal() as session:
            crud = TradeCRUD(session)
            crud.get_trades(pair, start, end)
