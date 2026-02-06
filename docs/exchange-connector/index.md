# Exchange Connector

The exchange connector module provides an abstraction layer for interacting with the Kraken
cryptocurrency exchange API. It handles authentication, rate limiting, and converts raw API
responses into domain objects.

## Quick Start

```python
from exchange_connector import (
    TradesConnector,
    TickerConnector,
    BalanceConnector,
    AddOrderConnector,
    KrakenApiError,  # Base exception for error handling
)

# Fetch historical trades (returns Trade domain objects)
trades_connector = TradesConnector()
trades = trades_connector.fetch('XXBTZGBP', since=1704067200000000000, until=1704153600000000000)

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
    result = order_connector.place('XXBTZGBP', 'buy', 100.0)  # Buy £100 worth
except KrakenApiError as e:
    print(f'API error: {e}')
```

## Contents

| Page                              | Description                                     |
| --------------------------------- | ----------------------------------------------- |
| [Architecture](architecture.md)   | Connector/service pattern and module structure  |
| [API Reference](api-reference.md) | Kraken API endpoints and authentication details |
