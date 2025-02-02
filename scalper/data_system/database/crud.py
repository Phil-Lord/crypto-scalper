import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Trade


class TradeCRUD:
    def __init__(self, session: Session):
        self.session = session

    def add_trades(self, raw_trades:  list[list[any]], pair: str) -> None:
        trades = self.__process_raw_trades(raw_trades, pair)

        stmt = text("""
            INSERT OR IGNORE INTO trades (trade_id, pair, price, volume, timestamp, side, order_type)
            VALUES (:trade_id, :pair, :price, :volume, :timestamp, :side, :order_type)
        """)

        self.session.execute(stmt, trades)
        self.session.commit()

    def get_trades(self, pair: str, start: int, end: int) -> pd.DataFrame:
        query = self.session.query(Trade).filter(
            Trade.pair == pair,
            Trade.timestamp.between(start, end)
        ).statement
        return pd.read_sql(query, self.session.bind)

    def __process_raw_trades(self, raw_trades: list[list[any]], pair: str) -> list[dict]:
        '''
        Converts raw trade data into a list of dictionaries matching the Trade model format.
        '''
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
