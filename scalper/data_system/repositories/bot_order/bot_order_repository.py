from abc import ABC, abstractmethod
from decimal import Decimal
from uuid import UUID

from data_system.models import BotOrder


class BotOrderRepository(ABC):
    @abstractmethod
    def add(self, bot_order: BotOrder) -> BotOrder:
        '''
        Adds a new order record.

        :param bot_order: The order record to add.
        :return: The added order record.
        '''
        pass

    @abstractmethod
    def get_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        '''
        Fetches orders for a certain bot ID.

        :param bot_id: Bot ID.
        :return: List of order records.
        '''
        pass

    @abstractmethod
    def update(self, bot_order: BotOrder) -> BotOrder:
        '''
        Updates an existing order record.

        :param bot_order: The order record to update.
        :return: The updated order record.
        '''
        pass

    @abstractmethod
    def get_placed_by_bot_id(self, bot_id: str) -> list[BotOrder]:
        '''
        Fetches orders with status 'placed' for a certain bot ID.

        :param bot_id: Bot ID.
        :return: List of order records.
        '''
        pass

    @abstractmethod
    def mark_filled(self, order_id: UUID, price: Decimal, volume: Decimal, fee: Decimal) -> BotOrder:
        '''
        Marks an order as filled with execution details from the exchange.

        Sets ``filled_at`` to the current UTC time internally.

        :param order_id: UUID of the order to update.
        :param price: Average execution price.
        :param volume: Executed volume.
        :param fee: Fee charged.
        :return: The updated order record.
        '''
        pass

    @abstractmethod
    def mark_failed(self, order_id: UUID, price: Decimal, volume: Decimal, fee: Decimal) -> BotOrder:
        '''
        Marks an order as failed (cancelled/expired on exchange) with whatever details are available.

        Sets ``filled_at`` to the current UTC time internally.
        Values may be non-zero if the order was partially filled before cancellation.

        :param order_id: UUID of the order to update.
        :param price: Price at cancellation.
        :param volume: Volume executed before cancellation.
        :param fee: Fee charged.
        :return: The updated order record.
        '''
        pass
