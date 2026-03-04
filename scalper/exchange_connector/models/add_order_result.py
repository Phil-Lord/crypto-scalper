from dataclasses import dataclass


@dataclass(frozen=True)
class AddOrderResult:
    '''
    Dataclass representing the result of placing an order on the exchange.

    This model transforms the raw Kraken AddOrder API response into a typed
    domain object, providing a platform-agnostic abstraction for order results.

    Attributes:
        txid (list[str] | None): Transaction IDs for the placed order (Kraken may return multiple).
            None when validate=True as no order is actually placed.
        order_description (str): Human-readable order description from the exchange.

    Note:
        This is an exchange domain model, not a database entity. For persisting
        order data, map this to the BotOrder model in data_system/models/.
    '''
    txid: list[str] | None
    order_description: str
