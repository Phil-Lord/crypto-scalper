# API Reference

This page documents the Kraken API endpoints used by the exchange connector.

## Authentication

Private endpoints require HMAC-SHA512 authentication. The `kraken_auth_utils` module handles
message signing and header construction; `KrakenApiClient._next_nonce()` generates the nonce.

1. **Nonce generation** — Nanosecond timestamp (`time.time_ns()`), monotonically advanced under
   a lock so two threads issuing requests in the same nanosecond still produce strictly
   increasing nonces. Required because APScheduler's thread pool can fire concurrent
   requests across bots.
2. **Message signing** — HMAC-SHA512 of nonce + POST data + endpoint.
3. **Header construction** — `API-Key` and `API-Sign` headers.

### Environment Variables

| Variable                    | Description          |
| --------------------------- | -------------------- |
| `KRAKEN_TRADING_API_KEY`    | Public API key       |
| `KRAKEN_TRADING_API_SECRET` | Private key (base64) |

## Public Endpoints

### Ticker

Get current price information for a trading pair.

- **Endpoint:** `GET /0/public/Ticker`
- **Connector:** `TickerConnector`
- **Service:** `TickerService`

```python
connector = TickerConnector()
ticker = connector.fetch('XXBTZGBP')
# Returns: {'a': ['50000.0', ...], 'b': ['49999.0', ...], ...}
```

### OHLC

Get candlestick data for a trading pair.

- **Endpoint:** `GET /0/public/OHLC`
- **Connector:** `OhlcConnector`
- **Service:** `OhlcService`

```python
connector = OhlcConnector()
candles = connector.fetch('XXBTZGBP', interval=1, start=1704067200)
# Returns: [[timestamp, open, high, low, close, vwap, volume, count], ...]
```

### Trades

Get historical trade data with pagination.

- **Endpoint:** `GET /0/public/Trades`
- **Connector:** `TradesConnector`
- **Service:** `TradesService`

```python
connector = TradesConnector()
trades = connector.fetch('XXBTZGBP', since=1704067200000000000, until=1704153600000000000)
# Returns: list[Trade]  (domain objects)
```

### Asset Pairs

Get trading pair information.

- **Endpoint:** `GET /0/public/AssetPairs`
- **Connector:** `AssetPairsConnector`
- **Service:** `AssetPairsService`

## Private Endpoints

### Balance

Get account balances (requires authentication).

- **Endpoint:** `POST /0/private/Balance`
- **Connector:** `BalanceConnector`
- **Service:** `BalanceService`

```python
connector = BalanceConnector()
balances = connector.fetch()
# Returns: {'XXBT': '1.5', 'ZGBP': '1000.0', ...}
```

### Add Order

Place a market order (requires authentication).

- **Endpoint:** `POST /0/private/AddOrder`
- **Connector:** `AddOrderConnector`
- **Service:** `AddOrderService`

```python
connector = AddOrderConnector()

# Place an actual order
result = connector.place('XXBTZGBP', 'buy', 100.0)
# Returns: AddOrderResult(txid=['ORDER-ID'], order_description='buy 100.00000000 XXBTZGBP @ market')

# Validate order without executing (for testing)
result = connector.place('XXBTZGBP', 'buy', 100.0, validate=True)
# Returns: AddOrderResult(txid=None, order_description='buy 100.00000000 XXBTZGBP @ market')
```

**Notes:**

- Buy orders use `viqc` flag (volume in quote currency).
- When `validate=True`, the order is validated but not executed, and `txid` will be `None`.
  This is what the trade executor's [dry-run mode](../trade-executor/index.md#dry-run-mode)
  uses to verify the OHLC → signal → order pipeline against production Kraken without
  placing real orders.

### Query Orders

Fetch execution details for one or more previously placed orders (requires authentication).

- **Endpoint:** `POST /0/private/QueryOrders`
- **Connector:** `QueryOrdersConnector`
- **Service:** `QueryOrdersService`

```python
from exchange_connector import QueryOrdersConnector

connector = QueryOrdersConnector()
results = connector.fetch(['ORDER-ID-1', 'ORDER-ID-2'])
# Returns: list[QueryOrderResult]
```

Multiple txids are sent in a single request — N orders cost one API call, not N. Used by
the trade executor to confirm fills (3× retry, 1s apart) right after placement and to
reconcile any leftover PLACED orders at the start of every interval.

`QueryOrderResult` is a frozen dataclass:

| Field    | Type               | Notes                                                  |
| -------- | ------------------ | ------------------------------------------------------ |
| `txid`   | `str`              | Kraken transaction ID (the order ID).                  |
| `price`  | `Decimal`          | Average executed price (`price` from Kraken response). |
| `volume` | `Decimal`          | Executed volume (`vol_exec` from Kraken response).     |
| `fee`    | `Decimal`          | Fee charged in quote currency.                         |
| `status` | `QueryOrderStatus` | `pending`, `open`, `closed`, `canceled`, or `expired`. |

`QueryOrderStatus` values map to the trade executor's order lifecycle:
`closed → FILLED`, `canceled` / `expired → FAILED`, `pending` / `open` → leave as PLACED
and reconcile next interval.

## Rate Limiting

Kraken enforces rate limits. The module handles this with:

1. **Detection** — `KrakenTooManyRequestsError` raised on `EGeneral:Too many requests`
2. **Retry** — Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
3. **Attempts** — Up to 5 retries before failure

## Error Handling

All Kraken-specific errors inherit from `KrakenApiError`, allowing you to catch all API errors with a single exception handler or handle specific error types:

```python
from exchange_connector import (
    TickerConnector,
    KrakenApiError,
    KrakenTooManyRequestsError,
    KrakenNetworkError,
)

try:
    connector = TickerConnector()
    data = connector.fetch('XXBTZGBP')
except KrakenTooManyRequestsError:
    # Rate limit hit - already auto-retried 5 times
    logger.error('Rate limit exceeded after retries')
except KrakenNetworkError:
    # Network connectivity issue
    logger.error('Network unavailable')
except KrakenApiError as e:
    # Catch any other Kraken API error
    logger.error(f'API error: {e}')
```

### Exception Types

| Exception                    | Raised When                                                | Handling   |
| ---------------------------- | ---------------------------------------------------------- | ---------- |
| `KrakenApiError`             | Base class for all Kraken errors                           | N/A        |
| `KrakenTooManyRequestsError` | Rate limit exceeded                                        | Auto-retry |
| `KrakenApiResponseError`     | API returns error (e.g., invalid pair, insufficient funds) | Propagated |
| `KrakenNetworkError`         | Network/HTTP request fails                                 | Propagated |
| `KrakenParseError`           | Response cannot be parsed as JSON                          | Propagated |
| `ValueError`                 | Invalid parameter (e.g., bad pair format)                  | Propagated |
