from dataclasses import asdict

from data_system.clients import SupabaseClient
from data_system.models import BotTick
from .bot_tick_repository import BotTickRepository


class SupabaseBotTickRepository(BotTickRepository):
    TABLE_NAME = 'bot_ticks'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()

    def add(self, bot_tick: BotTick) -> BotTick:
        record = asdict(bot_tick)
        record.pop('id', None)  # Remove id as it's auto-generated
        record['run_id'] = str(bot_tick.run_id)  # Convert UUID to string
        record['timestamp'] = bot_tick.timestamp.isoformat()
        if bot_tick.executed_at:
            record['executed_at'] = bot_tick.executed_at.isoformat()

        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
        return BotTick(**response.data[0])

    def get_by_bot_id(self, bot_id: str) -> list[BotTick]:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("bot_id", bot_id)
            .order("timestamp", desc=True)
            .execute()
        )
        return [BotTick(**row) for row in response.data]
