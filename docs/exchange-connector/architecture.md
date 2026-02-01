# Architecture

The exchange connector module uses a layered architecture to separate concerns and enable testing.

## Module Structure

```
exchange_connector/
├── __init__.py              # Public API exports
├── api/                     # Low-level HTTP client
│   ├── exceptions.py        # Custom exceptions
│   └── kraken_api_client.py # HTTP request handling
├── connectors/              # High-level interfaces
│   ├── base_connectors.py   # Abstract base classes
│   ├── trades_connector.py  # Trade data fetching
│   ├── ticker_connector.py  # Current price data
│   └── ...                  # Other connectors
├── services/                # Business logic layer
│   ├── kraken_service.py    # Base service with retry logic
│   ├── trades_service.py    # Trade fetching with pagination
│   └── ...                  # Other services
└── kraken_utils/            # Authentication utilities
    └── kraken_auth_utils.py # API key signing
```

## Layer Responsibilities

### API Layer (`api/`)

The lowest level, handling raw HTTP communication:

- **KrakenApiClient** — Makes HTTP requests, parses JSON, handles HTTP errors
- **Exceptions** — Custom exceptions like `KrakenTooManyRequestsError`

### Services Layer (`services/`)

Business logic and API-specific behaviour:

- **KrakenService** — Base class with retry logic (exponential backoff) and validation
- **Specific Services** — Endpoint-specific logic (e.g., `TradesService` handles pagination)

### Connectors Layer (`connectors/`)

High-level interfaces for other modules:

- **FetchConnector** — Abstract base for data fetching
- **PlaceConnector** — Abstract base for order placement
- **Specific Connectors** — Convert API responses to domain objects

## Design Patterns

### Dependency Injection

Connectors accept an optional `KrakenApiClient` for testing:

```python
class TradesConnector(FetchConnector):
    def __init__(self, client: KrakenApiClient = None):
        self.client = client or KrakenApiClient()
        self.service = TradesService(self.client)
```

### Retry with Exponential Backoff

The `KrakenService` base class uses `tenacity` for automatic retries on rate limiting:

```python
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(KrakenTooManyRequestsError)
)
def make_request(self, method: str, endpoint: str, params: dict) -> dict:
    ...
```

### Domain Object Conversion

Connectors convert raw API data to domain objects:

```python
def _to_domain(self, raw_trades: list[list], pair: str) -> list[Trade]:
    return [
        Trade(
            trade_id=int(raw[6]),
            pair=pair,
            price=float(raw[0]),
            ...
        )
        for raw in raw_trades
    ]
```

## Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌─────────────┐
│  Connector  │────▶│   Service    │────▶│   API Client  │────▶│  Kraken API │
│ (interface) │     │ (retry/logic)│     │ (HTTP/auth)   │     │  (external) │
└─────────────┘     └──────────────┘     └───────────────┘     └─────────────┘
       ▲                  ▲                      ▲                      │
       │                  │                      │                      │
       │                  │         Raw JSON Response                   │
       │                  │◀─────────────────────────────────────────────┘
       │                  │
       │     Dict (result data)
       │◀─────────────────┘
       │
       │ (Optional)
       │ Conversion
       ▼
┌─────────────┐
│   Domain    │
│   Objects   │
└─────────────┘
```
