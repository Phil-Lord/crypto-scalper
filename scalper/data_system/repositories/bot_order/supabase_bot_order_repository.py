from dataclasses import asdict

from data_system.clients import SupabaseClient
from data_system.models import BotOrder
from .bot_order_repository import BotOrderRepository


class SupabaseBotOrderRepository(BotOrderRepository):
    TABLE_NAME = 'bot_orders'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()

    def add(self, bot_order: BotOrder) -> BotOrder:
        # Convert UUIDs to strings and datetime to ISO format
        record = asdict(bot_order)
        record['id'] = str(bot_order.id)
        record['run_id'] = str(bot_order.run_id)
        record['executed_at'] = bot_order.executed_at.isoformat()

        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
        return BotOrder(**response.data[0])

    def get_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("bot_id", bot_id)
            .order("executed_at", desc=True)
            .execute()
        )
        return [BotOrder(**row) for row in response.data]
