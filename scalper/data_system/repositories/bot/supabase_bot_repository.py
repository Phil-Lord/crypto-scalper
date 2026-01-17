from dataclasses import asdict

from data_system.clients import SupabaseClient
from data_system.models import Bot
from .bot_repository import BotRepository


class SupabaseBotRepository(BotRepository):
    TABLE_NAME = 'bots'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()

    def add(self, bot: Bot) -> Bot:
        record = asdict(bot)
        record['created_at'] = bot.created_at.isoformat()
        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
        return Bot(**response.data[0])

    def get(self, id: str) -> Bot:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select("*")
            .eq("id", id)
            .execute()
        )
        return Bot(**response.data[0])
