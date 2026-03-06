from dataclasses import asdict
from datetime import datetime
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
        # Convert UUIDs to strings and datetime to ISO format
        record = asdict(bot_order)
        record['id'] = str(bot_order.id)
        record['run_id'] = str(bot_order.run_id)
        record['placed_at'] = bot_order.placed_at.isoformat()
        record['filled_at'] = bot_order.filled_at.isoformat() if bot_order.filled_at else None

        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
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

    def _to_bot_order(self, data: dict) -> BotOrder:
        data['id'] = UUID(data['id'])
        data['run_id'] = UUID(data['run_id'])

        data['side'] = Side(data['side'])
        data['status'] = OrderStatus(data['status'])
        data['placed_at'] = datetime.fromisoformat(data['placed_at'])

        data['filled_at'] = datetime.fromisoformat(data['filled_at']) if data['filled_at'] else None
        data['price'] = Decimal(data['price']) if data['price'] is not None else None
        data['volume'] = Decimal(data['volume']) if data['volume'] is not None else None
        data['fee'] = Decimal(data['fee']) if data['fee'] is not None else None

        return BotOrder(**data)
