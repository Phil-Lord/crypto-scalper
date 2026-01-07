import pandas as pd
from sqlalchemy import func, text

from data_system.clients import SQLAlchemyClient
from data_system.models import Trade
from .trade_repository import TradeRepository


class SqlAlchemyTradeRepository(TradeRepository):
    def __init__(self) -> None:
        self.client = SQLAlchemyClient()

    def add(self, raw_trades: list[list[any]], pair: str) -> None:
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

    def get(self, pair: str, start: int = None, end: int = None) -> list[dict]:
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
