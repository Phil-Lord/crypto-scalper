# API Reference

This page documents the Kraken API endpoints used by the exchange connector.

## Authentication

Private endpoints require HMAC-SHA512 authentication. The `kraken_auth_utils` module handles:

1. **Nonce generation** — Millisecond timestamp to prevent replay attacks
2. **Message signing** — HMAC-SHA512 of nonce + POST data + endpoint
3. **Header construction** — `API-Key` and `API-Sign` headers

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
result = connector.place('XXBTZGBP', 'buy', 100.0)  # Buy £100 worth
# Returns: {'txid': ['ORDER-ID'], ...}
```

**Note:** Buy orders use `viqc` flag (volume in quote currency).

## Rate Limiting

Kraken enforces rate limits. The module handles this with:

1. **Detection** — `KrakenTooManyRequestsError` raised on `EGeneral:Too many requests`
2. **Retry** — Exponential backoff: 1s, 2s, 4s, 8s, 16s (max 30s)
3. **Attempts** — Up to 5 retries before failure

## Error Handling

| Error            | Exception                    | Handling   |
| ---------------- | ---------------------------- | ---------- |
| Rate limited     | `KrakenTooManyRequestsError` | Auto-retry |
| Other API errors | `RuntimeError`               | Propagated |
| Network errors   | `RuntimeError`               | Propagated |
| Invalid pair     | `ValueError`                 | Propagated |
