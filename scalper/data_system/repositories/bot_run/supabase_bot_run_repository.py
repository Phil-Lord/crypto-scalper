from dataclasses import asdict

from supabase import Client

from data_system.models import BotRun
from .bot_run_repository import BotRunRepository


class SupabaseBotRunRepository(BotRunRepository):
    TABLE_NAME = 'bot_runs'

    def __init__(self, client: Client) -> None:
        self.client = client

    def add(self, bot_run: BotRun) -> BotRun:
        # Convert UUID to string and datetimes to ISO format
        record = asdict(bot_run)
        record['id'] = str(bot_run.id)
        record['started_at'] = bot_run.started_at.isoformat()
        if bot_run.completed_at:
            record['completed_at'] = bot_run.completed_at.isoformat()

        response = (self.client.table(self.TABLE_NAME).insert(record).execute())
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
