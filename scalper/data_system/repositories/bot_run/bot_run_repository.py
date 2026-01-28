from abc import ABC, abstractmethod

from data_system.models import BotRun


class BotRunRepository(ABC):
    @abstractmethod
    def add(self, bot_run: BotRun) -> BotRun:
        '''
        Adds a new bot run record.

        :param bot_run: The bot run record to add.
        :return: The added bot run record.
        '''
        pass

    @abstractmethod
    def get(self, id: str) -> BotRun | None:
        '''
        Fetches a bot run by its ID.

        :param id: Bot run ID.
        :return: The bot run record, or None if not found.
        '''
        pass
