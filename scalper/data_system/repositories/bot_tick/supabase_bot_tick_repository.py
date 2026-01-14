from dataclasses import asdict

from data_system.clients import SupabaseClient
from data_system.models import BotTick
from .bot_tick_repository import BotTickRepository


class SupabaseBotTickRepository(BotTickRepository):
    TABLE_NAME = 'bot_ticks'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()

    def add(self, result: BotTick) -> BotTick:
        response = (self.client.table(self.TABLE_NAME).insert(asdict(result)).execute())
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
