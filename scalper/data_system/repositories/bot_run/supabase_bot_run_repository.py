from dataclasses import asdict
from datetime import datetime
from uuid import UUID

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
        return self._to_bot_run(response.data[0])

    def get(self, id: UUID) -> BotRun | None:
        response = (
            self.client
            .table(self.TABLE_NAME)
            .select('*')
            .eq('id', str(id))
            .execute()
        )
        if not response.data:
            return None
        return self._to_bot_run(response.data[0])

    def _to_bot_run(self, data: dict) -> BotRun:
        data['id'] = UUID(data['id'])
        data['started_at'] = datetime.fromisoformat(data['started_at'])
        if data.get('completed_at'):
            data['completed_at'] = datetime.fromisoformat(data['completed_at'])
        return BotRun(**data)
