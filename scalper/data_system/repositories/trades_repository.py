import pandas as pd

from .base_repository import Repository
from data_system.database import SessionLocal, TradeCRUD


class TradesRepository(Repository):
    def add(self, trades: list[list[any]], pair: str) -> None:
        ''' Insert a list of trades for a certain pair in their raw format from the Kraken API. '''
        print(f'Inserting {pair} trades.')
        with SessionLocal() as session:
            crud = TradeCRUD(session)
            crud.add_trades(trades, pair)

    def get(self, pair: str, start: int = None, end: int = None) -> pd.DataFrame:
        ''' Fetch trades for a certain pair between a start and end date. '''
        print(f'Fetching {pair} trades from {start if start else 'start'} to {end if end else 'end'}.')
        with SessionLocal() as session:
            crud = TradeCRUD(session)
            return crud.get_trades(pair, start, end)
