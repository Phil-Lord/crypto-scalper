from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from supabase import Client

from data_system.models import BotOrder
from data_system.models.bot_order_model import OrderStatus, Side
from .bot_order_repository import BotOrderRepository


class SupabaseBotOrderRepository(BotOrderRepository):
    TABLE_NAME = 'bot_orders'

    def __init__(self, client: Client) -> None:
        self.client = client

    def add(self, bot_order: BotOrder) -> BotOrder:
        response = self.client.table(self.TABLE_NAME).insert(self._to_record(bot_order)).execute()
        if not response.data:
            raise RuntimeError(f'Insert into {self.TABLE_NAME} returned no data')
        return self._to_bot_order(response.data[0])

    def get_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select('*')
            .eq('bot_id', bot_id)
            .order('placed_at', desc=True)
            .execute()
        )
        return [self._to_bot_order(row) for row in response.data]

    def update(self, bot_order: BotOrder) -> BotOrder:
        payload = {
            'status': bot_order.status.value,
            'tick_id': bot_order.tick_id,
            'filled_at': bot_order.filled_at.isoformat() if bot_order.filled_at else None,
            'price': str(bot_order.price) if bot_order.price is not None else None,
            'volume': str(bot_order.volume) if bot_order.volume is not None else None,
            'fee': str(bot_order.fee) if bot_order.fee is not None else None,
        }
        response = (
            self.client
            .table(self.TABLE_NAME)
            .update(payload)
            .eq('id', str(bot_order.id))
            .execute()
        )
        if not response.data:
            raise ValueError(f'BotOrder with id {bot_order.id} not found')
        return self._to_bot_order(response.data[0])

    def get_placed_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select('*')
            .eq('bot_id', bot_id)
            .eq('status', OrderStatus.PLACED.value)
            .order('placed_at', desc=True)
            .execute()
        )
        return [self._to_bot_order(row) for row in response.data]

    def mark_filled(self, order_id: UUID, price: Decimal, volume: Decimal, fee: Decimal) -> BotOrder:
        return self._mark_terminal(order_id, OrderStatus.FILLED, price, volume, fee)

    def mark_failed(self, order_id: UUID, price: Decimal, volume: Decimal, fee: Decimal) -> BotOrder:
        return self._mark_terminal(order_id, OrderStatus.FAILED, price, volume, fee)

    def _mark_terminal(self, order_id: UUID, status: OrderStatus, price: Decimal, volume: Decimal, fee: Decimal) -> BotOrder:
        payload = {
            'status': status.value,
            'filled_at': datetime.now(timezone.utc).isoformat(),
            'price': str(price),
            'volume': str(volume),
            'fee': str(fee),
        }
        response = (
            self.client
            .table(self.TABLE_NAME)
            .update(payload)
            .eq('id', str(order_id))
            .eq('status', OrderStatus.PLACED.value)
            .execute()
        )
        if not response.data:
            raise ValueError(f'BotOrder with id {order_id} not found or already resolved')
        return self._to_bot_order(response.data[0])

    def _to_record(self, bot_order: BotOrder) -> dict:
        record = asdict(bot_order)

        # UUIDs to strings
        record['id'] = str(bot_order.id)
        record['run_id'] = str(bot_order.run_id)

        # Datetimes to ISO format strings
        record['placed_at'] = bot_order.placed_at.isoformat()
        record['filled_at'] = bot_order.filled_at.isoformat() if bot_order.filled_at else None

        # Decimals to strings to avoid floating point issues in JSON
        record['price'] = str(bot_order.price) if bot_order.price is not None else None
        record['volume'] = str(bot_order.volume) if bot_order.volume is not None else None
        record['fee'] = str(bot_order.fee) if bot_order.fee is not None else None

        return record

    def _to_bot_order(self, data: dict) -> BotOrder:
        data['id'] = UUID(data['id'])
        data['run_id'] = UUID(data['run_id'])

        data['side'] = Side(data['side'])
        data['status'] = OrderStatus(data['status'])
        data['placed_at'] = datetime.fromisoformat(data['placed_at'])

        data['filled_at'] = datetime.fromisoformat(data['filled_at']) if data['filled_at'] else None
        data['price'] = Decimal(str(data['price'])) if data['price'] is not None else None
        data['volume'] = Decimal(str(data['volume'])) if data['volume'] is not None else None
        data['fee'] = Decimal(str(data['fee'])) if data['fee'] is not None else None

        return BotOrder(**data)
