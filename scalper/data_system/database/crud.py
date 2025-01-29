from sqlalchemy.orm import Session

from .models import Trade


class TradeCRUD:
    def __init__(self, session: Session):
        self.session = session

    def add_trades(self, raw_trades:  list[list[any]], pair: str) -> None:
        trades = self.__process_raw_trades(raw_trades, pair)
        self.session.bulk_save_objects(trades)
        self.session.commit()

    def get_trades(self, pair: str, start: int, end: int) -> list[Trade]:
        return self.session.query(Trade).filter(
            Trade.pair == pair,
            Trade.timestamp.between(start, end)
        ).all()

    def __process_raw_trades(self, raw_trades: list[list[any]], pair: str) -> list[Trade]:
        '''
        Converts raw trade data into a list of Trade model objects, dropping the miscellaneous column.
        '''
        trades = []
        for trade in raw_trades:
            trades.append(Trade(
                price=float(trade[0]),
                volume=float(trade[1]),
                timestamp=float(trade[2]),
                side=str(trade[3]),
                order_type=str(trade[4]),
                trade_id=int(trade[6]),
                pair=pair
            ))
        return trades
