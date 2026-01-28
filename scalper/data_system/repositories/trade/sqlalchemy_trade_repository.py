from dataclasses import asdict

from sqlalchemy import text

from data_system.clients import SQLAlchemyClient
from data_system.models import Trade
from .trade_repository import TradeRepository


class SQLAlchemyTradeRepository(TradeRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, trades: list[Trade]) -> None:
        if not trades:
            return

        print(f'Inserting {len(trades)} trades for {trades[0].pair}.')
        with self.client.session() as session:
            records = [asdict(t) for t in trades]

            stmt = text("""
                INSERT OR IGNORE INTO trades (trade_id, pair, price, volume, timestamp, side, order_type)
                VALUES (:trade_id, :pair, :price, :volume, :timestamp, :side, :order_type)
            """)

            session.execute(stmt, records)

    def get(self, pair: str, start: float = None, end: float = None) -> list[Trade]:
        with self.client.session() as session:
            # Get min/max timestamps if not provided
            if start is None:
                start = session.execute(
                    text("SELECT MIN(timestamp) FROM trades WHERE pair = :pair"),
                    {"pair": pair}
                ).scalar()

            if end is None:
                end = session.execute(
                    text("SELECT MAX(timestamp) FROM trades WHERE pair = :pair"),
                    {"pair": pair}
                ).scalar()

            print(f'Fetching {pair} trades from {start} to {end}.')

            query = text("""
                SELECT trade_id, pair, price, volume, timestamp, side, order_type
                FROM trades
                WHERE pair = :pair AND timestamp BETWEEN :start AND :end
                ORDER BY timestamp ASC
            """)

            result = session.execute(query, {"pair": pair, "start": start, "end": end})
            rows = result.fetchall()

            return [
                Trade(
                    trade_id=row[0],
                    pair=row[1],
                    price=row[2],
                    volume=row[3],
                    timestamp=row[4],
                    side=row[5],
                    order_type=row[6]
                )
                for row in rows
            ]
