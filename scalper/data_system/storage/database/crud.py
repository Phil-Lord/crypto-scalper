from sqlalchemy.orm import Session

from .models import Trade


class TradeCRUD:
    def __init__(self, session: Session):
        self.session = session

    def insert_trades(self, trades: list[Trade]):
        self.session.bulk_save_objects(trades)
        self.session.commit()

    def get_trades_for_pair(self, pair: str, start: int, end: int):
        return self.session.query(Trade).filter(
            Trade.pair == pair,
            Trade.timestamp.between(start, end)
        ).all()
