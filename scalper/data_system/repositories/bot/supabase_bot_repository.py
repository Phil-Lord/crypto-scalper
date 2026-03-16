from dataclasses import asdict
from datetime import datetime

from supabase import Client

from data_system.models import Bot
from .bot_repository import BotRepository


class SupabaseBotRepository(BotRepository):
    TABLE_NAME = 'bots'

    def __init__(self, client: Client) -> None:
        self.client = client

    def add(self, bot: Bot) -> Bot:
        response = self.client.table(self.TABLE_NAME).insert(self._to_record(bot)).execute()
        if not response.data:
            raise RuntimeError(f'Insert into {self.TABLE_NAME} returned no data')
        return self._to_bot(response.data[0])

    def get(self, id: str) -> Bot | None:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select('*')
            .eq('id', id)
            .execute()
        )
        if not response.data:
            return None
        return self._to_bot(response.data[0])

    def _to_record(self, bot: Bot) -> dict:
        record = asdict(bot)
        record['created_at'] = bot.created_at.isoformat()
        return record

    def _to_bot(self, data: dict) -> Bot:
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        return Bot(**data)
