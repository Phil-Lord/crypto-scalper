from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from supabase import Client

from data_system.models import BotOrder
from data_system.models.bot_order_model import Side
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
        record['executed_at'] = bot_order.executed_at.isoformat()

        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
        return self._to_bot_order(response.data[0])

    def get_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("bot_id", bot_id)
            .order("executed_at", desc=True)
            .execute()
        )
        return [self._to_bot_order(row) for row in response.data]

    def _to_bot_order(self, data: dict) -> BotOrder:
        data['id'] = UUID(data['id'])
        data['run_id'] = UUID(data['run_id'])
        data['executed_at'] = datetime.fromisoformat(data['executed_at'])
        data['price'] = Decimal(data['price'])
        data['fee'] = Decimal(data['fee'])
        data['side'] = Side(data['side'])
        return BotOrder(**data)
