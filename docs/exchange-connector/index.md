# Exchange Connector

The exchange connector module provides an abstraction layer for interacting with the Kraken
cryptocurrency exchange API. It handles authentication, rate limiting, and converts raw API
responses into domain objects.

## Quick Start

```python
from decimal import Decimal

from exchange_connector import (
    TradesConnector,
    TickerConnector,
    OhlcConnector,
    BalanceConnector,
    AddOrderConnector,
    QueryOrdersConnector,
    KrakenApiError,  # Base exception for error handling
)

# Fetch historical trades (returns Trade domain objects)
trades_connector = TradesConnector()
trades = trades_connector.fetch('XXBTZGBP', start=1704067200000000000, end=1704153600000000000)

# Get current price
ticker_connector = TickerConnector()
price_data = ticker_connector.fetch('XXBTZGBP')
current_price = float(price_data['c'][0])

# Check account balance
balance_connector = BalanceConnector()
balances = balance_connector.fetch()

# Place a market order with error handling
order_connector = AddOrderConnector()
try:
    result = order_connector.place('XXBTZGBP', 'buy', Decimal('100.0'))  # Buy £100 worth
except KrakenApiError as e:
    logger.error(f'API error: {e}')

# Confirm fill details for one or more orders
query_connector = QueryOrdersConnector()
fills = query_connector.fetch([result.txid[0]])  # list[QueryOrderResult]
```

## Contents

| Page                              | Description                                     |
| --------------------------------- | ----------------------------------------------- |
| [Architecture](architecture.md)   | Connector/service pattern and module structure  |
| [API Reference](api-reference.md) | Kraken API endpoints and authentication details |
