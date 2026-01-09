from sqlalchemy import BigInteger, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from .base_model import Model


class Trade(Model):
    '''
    ORM-mapped class for storing trade data.

    This table is designed to handle trade data from multiple trading pairs with
    the following considerations:

    1.  **Primary Key**: A composite primary key (`trade_id`, `pair`) ensures that
        trade IDs are unique per trading pair, aligning with how trade IDs are generated
        by the Kraken API.

    2.  **Indexes**: A composite index on `pair` and `timestamp` optimises queries filtering
        by pair and time ranges, the most common use case. The single-column index on `pair`
        is included for queries fetching all trades for a specific pair without a time constraint.

    3.  **Column Types**: `BIGINT` is used for `trade_id` to accommodate high trade volumes and
        `FLOAT` is used for `timestamp` to differentiate between trades made in the same second.
    '''
    __tablename__ = 'trades'

    trade_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pair: Mapped[str] = mapped_column(String(15), primary_key=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    timestamp: Mapped[float] = mapped_column(Float, nullable=False)
    side: Mapped[str] = mapped_column(String(1), nullable=False)
    order_type: Mapped[str] = mapped_column(String(1), nullable=False)

    __table_args__ = (
        Index('ix_trades_pair_timestamp', 'pair', 'timestamp'),
        Index('ix_trades_pair', 'pair')
    )
