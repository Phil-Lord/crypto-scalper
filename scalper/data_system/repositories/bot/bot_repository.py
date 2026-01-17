from abc import ABC, abstractmethod

from data_system.models import Bot


class BotRepository(ABC):
    @abstractmethod
    def add(self, bot: Bot) -> Bot:
        '''
        Adds a new bot record.

        :param bot: The bot record to add.
        :return: The added bot record.
        '''
        pass

    @abstractmethod
    def get(self, id: str) -> Bot:
        '''
        Fetches a bot by its ID.

        :param id: Bot ID.
        :return: The bot record.
        '''
        pass
