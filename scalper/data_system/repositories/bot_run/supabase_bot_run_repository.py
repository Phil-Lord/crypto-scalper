from dataclasses import asdict

from data_system.clients import SupabaseClient
from data_system.models import BotRun
from .bot_run_repository import BotRunRepository


class SupabaseBotRunRepository(BotRunRepository):
    TABLE_NAME = 'bot_runs'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()

    def add(self, result: BotRun) -> BotRun:
        response = (self.client.table(self.TABLE_NAME).insert(asdict(result)).execute())
        return BotRun(**response.data[0])

    def get(self, id: str) -> BotRun:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("id", id)
            .execute()
        )
        return BotRun(**response.data[0])
