from data_system.clients import SupabaseClient
from .bot_repository import BotRepository


class SupabaseBotRepository(BotRepository):
    TABLE_NAME = 'bots'

    def __init__(self) -> None:
        self.client = SupabaseClient().get_client()
