import pandas as pd
from sqlalchemy import func, text

from .base_service import Service
from data_system.clients import SQLAlchemyClient
from data_system.models import Trade


class TradesService(Service):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, raw_trades: list[list[any]], pair: str) -> None:
        '''
        Inserts a list of trades for a certain pair in their raw format from the Kraken API.

        :param raw_trades: List of trade lists, e.g. [[price, vol, time, b/s, m/l, misc, id], ...].
        :param pair: Trading pair identifier, e.g. 'XXBTZGBP'.
        '''
        print(f'Inserting {pair} trades.')
        session = self.client.connect()
        try:
            trades = self.__process_raw_trades(raw_trades, pair)

            stmt = text("""
                INSERT OR IGNORE INTO trades (trade_id, pair, price, volume, timestamp, side, order_type)
                VALUES (:trade_id, :pair, :price, :volume, :timestamp, :side, :order_type)
            """)

            session.execute(stmt, trades)
            session.commit()
        finally:
            session.close()

    def get(self, pair: str, start: int = None, end: int = None) -> pd.DataFrame:
        '''
        Fetches trades for a certain pair between a start and end date.

        :param pair: Trading pair identifier, e.g. 'XXBTZGBP'.
        :param start: Start timestamp. If None, fetches from the earliest trade.
        :param end: End timestamp. If None, fetches up to the latest trade.

        :return: Trades Dataframe.
        '''
        print(f'Fetching {pair} trades from {start or 'start'} to {end or 'end'}.')
        session = self.client.connect()
        try:
            start = start or session.query(func.min(Trade.timestamp)).filter(
                Trade.pair == pair).scalar()
            end = end or session.query(func.max(Trade.timestamp)).filter(
                Trade.pair == pair).scalar()

            query = session.query(Trade).filter(
                Trade.pair == pair,
                Trade.timestamp.between(start, end)
            ).statement

            return pd.read_sql(query, session.bind)
        finally:
            session.close()

    def __process_raw_trades(self, raw_trades: list[list[any]], pair: str) -> list[dict]:
        ''' Converts raw trade data into a list of dictionaries matching the Trade model format. '''
        return [
            {
                'trade_id': int(trade[6]),
                'pair': pair,
                'price': float(trade[0]),
                'volume': float(trade[1]),
                'timestamp': float(trade[2]),
                'side': str(trade[3]),
                'order_type': str(trade[4])
            }
            for trade in raw_trades
        ]
