# Copilot Instructions

These instructions guide AI agents working on the `crypto-scalper` project. Standards are derived
from the Data System module—the project's reference implementation.

---

## Project Overview

A cryptocurrency scalping bot with:

- **Backtesting Engine** — Local parameter optimisation using Optuna
- **Data System** — Multi-backend storage (SQLAlchemy/SQLite + Supabase/PostgreSQL)
- **Exchange Connector** — Kraken API integration
- **Strategy Manager** — Trading strategy implementations
- **Trade Executor** — Live trading execution

---

# Part 1: Universal Standards

These standards apply to **all code** in the project.

---

## Python Style

### Language Version

- **Python 3.12+** — Use modern syntax throughout
- Use `str | None` not `Optional[str]`
- Use `list[Trade]` not `List[Trade]`

### Formatting

- **PEP 8** with 100-character line limit
- **Single quotes** for strings, even docstrings
- **Trailing commas** in multi-line collections
- **No unused imports** — Keep imports minimal and organised

### Imports

Organise imports in this order, separated by blank lines:

1. Standard library
2. Third-party packages
3. Local modules (relative imports within a module, absolute for cross-module)

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone

import pytest

from data_system.models import Trade
from .trade_repository import TradeRepository
```

### Type Hints

Always use type hints for function signatures:

```python
def get(self, pair: str, start: float = None, end: float = None) -> list[Trade]:
```

---

## Models & Data Structures

### Dataclass Conventions

Domain models should be **frozen dataclasses**:

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class Bot:
    '''
    Dataclass representing a trading bot configuration.

    Attributes:
        id (str): Human-readable unique identifier for the bot, e.g., `btc_1m_001`.
        pair (str): Trading pair in Kraken format, e.g., `XXBTZGBP`.
    '''
    id: str
    pair: str
    strategy_name: str
    interval: int
    parameters: dict[str, Any]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

Key patterns:

- Use `frozen=True` for immutability
- Required fields first, optional/defaulted fields last
- Use `field(default_factory=...)` for mutable defaults
- Document all attributes in the docstring

### Enums

Use `str, Enum` for string-compatible enums:

```python
class Signal(str, Enum):
    BUY = 'buy'
    HOLD = 'hold'
    SELL = 'sell'
```

### Type Choices

| Use Case                 | Type       | Notes                           |
| ------------------------ | ---------- | ------------------------------- |
| IDs (exchange)           | `int`      | e.g., `trade_id: int`           |
| IDs (human-readable)     | `str`      | e.g., `bot_id: 'btc_1m_001'`    |
| IDs (database-generated) | `UUID`     | e.g., `run_id: UUID`            |
| Timestamps (Unix)        | `float`    | Sub-second precision            |
| Timestamps (Datetime)    | `datetime` | Always timezone-aware (UTC)     |
| Money (backtesting)      | `float`    | Speed over precision            |
| Money (live trading)     | `Decimal`  | Precision for real transactions |

---

## Documentation

### When to Write Docstrings

Docstrings are required for:

- **Domain models (dataclasses)** — Document all attributes
- **Public API functions** — Repository methods, service functions
- **Complex logic** — Anything non-obvious
- **Methods with non-obvious parameters** — Document parameter meaning and units (e.g., nanoseconds vs seconds)

Docstrings are NOT required for:

- **Constants and config values** — Self-explanatory by name
- **Simple utility functions** — If the name and signature are clear
- **Internal helpers** — Short functions with obvious purpose
- **Simple exception classes** — If the class name is self-documenting (e.g., `KrakenTooManyRequestsError`)
- **Methods that only delegate** — If they just call another method with the same semantics

**Guideline:** Avoid over-explaining self-documenting code or duplicating docstrings from called methods. Focus docstrings on understanding parameters, return types, and non-obvious behavior. If reading a docstring would be slower than reading the code itself, skip the docstring.

### Docstring Style

When writing docstrings, use **reStructuredText** style:

```python
def get(self, pair: str, start: float = None, end: float = None) -> list[Trade]:
    '''
    Fetches trades for a trading pair within a time range.

    :param pair: Trading pair identifier, e.g., 'XXBTZGBP'.
    :param start: Start timestamp (Unix seconds). If None, fetches from earliest.
    :param end: End timestamp (Unix seconds). If None, fetches up to latest.
    :return: List of Trade domain objects.
    '''
```

For dataclasses, document attributes in the class docstring:

```python
@dataclass(frozen=True)
class Trade:
    '''
    Dataclass representing a single trade from the exchange.

    Attributes:
        trade_id (int): Unique trade identifier from the exchange.
        pair (str): Trading pair identifier, e.g., 'XXBTZGBP'.

    Note:
        Primary key is composite (trade_id, pair) since trade IDs are only
        unique per trading pair on Kraken.
    '''
```

### Module Documentation

Create markdown docs in `/docs/` for significant modules:

- `index.md` — Overview and contents table
- Additional pages as needed for architecture, schemas, etc.

### Architecture Decision Log

Record non-obvious architectural decisions in `/docs/architecture-decision-log.md`. Add an entry
when:

- The decision isn't clear from the code itself
- Future-you might ask *"why did I do it this way?"*
- There were trade-offs worth documenting

### Prompt Files

Reusable prompts live in `.github/prompts/`. When a task becomes repeatable (e.g., auditing
modules, adding strategies), consider creating a prompt file for it.

---

## Testing

### Framework & Configuration

- **pytest** with **pytest-mock** for mocking
- Tests live in `scalper/tests/`, mirroring source structure
- Python path configured in `pytest.ini`

### Test Coverage Philosophy

**Test behavior, not just code paths:**

- ✅ **Do test:** Retry logic, error propagation, pagination, validation edge cases
- ✅ **Do test:** Integration points between layers
- ❌ **Don't just test:** Happy path scenarios with everything mocked
- ❌ **Don't just test:** Simple delegation (connector calling service)

### Naming Conventions

| Element     | Convention                                | Example                                    |
| ----------- | ----------------------------------------- | ------------------------------------------ |
| Test file   | `test_{module}.py`                        | `test_trade_model.py`                      |
| Test class  | `Test{ClassName}`                         | `TestTrade`                                |
| Test method | `test_{action}_{condition}_{expectation}` | `test_get_returns_none_when_bot_not_found` |

### Test Structure

Use the **Given/When/Then** pattern with comments:

```python
def test_add_inserts_trades(self, mock_client, mock_session, sample_trade: Trade):
    # Given
    repository = SQLAlchemyTradeRepository(mock_client)

    # When
    repository.add([sample_trade])

    # Then
    mock_session.execute.assert_called_once()
```

For simple tests, `# When / Then` can be combined:

```python
def test_trade_is_frozen(self, sample_trade_data):
    # Given
    trade = Trade(**sample_trade_data)

    # When / Then
    with pytest.raises(AttributeError):
        trade.price = 60000.0
```

### Pytest Markers

Use hierarchical markers for granular test selection:

```python
@pytest.mark.data_system      # Module level
@pytest.mark.repositories     # Category level
@pytest.mark.supabase_bot_repository  # Class level
class TestSupabaseBotRepository:
```

Register all markers in `pytest.ini`.

### Makefile Targets

Add `make` targets for running module tests:

```makefile
# In .PHONY declaration
.PHONY: test test/utils test/data_system

# Module-level target
test/utils:
	pytest -m utils

# Category-level target (for larger modules)
test/data_system/models:
	pytest -m "data_system and models"
```

### Fixtures

- Define fixtures in the test class when class-specific
- Use descriptive names: `sample_trade_data`, `mock_supabase_client`
- Type hint fixture return values

```python
@pytest.fixture
def sample_trade(self) -> Trade:
    return Trade(
        trade_id=123456789,
        pair='XXBTZGBP',
        price=50000.0,
        ...
    )
```

### Integration Tests

Integration tests verify that **multiple layers work together** correctly by mocking only at system boundaries.

**Purpose:** Catch issues in layer interactions, data transformations, and parameter passing that unit tests miss.

**Location:** `scalper/tests/integration/`

**What makes a test an integration test:**
- Mocks **only external systems** (HTTP, database connections, file I/O)
- Lets **all our code run** (connectors, services, clients, transformations)
- Tests **realistic end-to-end scenarios** with actual data flows

**Markers:**
- `@pytest.mark.integration` — Module-level marker
- `@pytest.mark.{module}_integration` — Specific integration test suite

**When to write integration tests:**
- Testing **multi-layer interactions** (connector → service → client stack)
- Verifying **domain transformations** with realistic API data
- Testing **parameter handling** through multiple function calls
- Validating **error propagation** from low-level errors to high-level handlers

**When NOT to write integration tests:**
- Simple unit-level functionality (use unit tests instead)
- Testing individual methods in isolation (use unit tests instead)
- Complex business logic that doesn't involve layer interactions (use unit tests instead)

**Common patterns:**

```python
@pytest.mark.integration
@pytest.mark.exchange_connector_integration
class TestExchangeConnectorIntegration:
    '''Integration tests for the connector -> service -> client stack.'''

    def test_full_stack_integration(self, mock_api_response):
        # Given
        connector = SomeConnector()
        
        # When - Mock HTTP, let everything else run
        with patch('time.sleep'), patch('requests.Session.request') as mock_request:
            mock_response = Mock()
            mock_response.json.return_value = mock_api_response
            mock_response.raise_for_status.return_value = None
            mock_request.return_value = mock_response
            
            result = connector.fetch(params)
        
        # Then
        assert result is not None
        # Verify transformation, parameter handling, etc.
```

**Critical considerations:**
- Mock `time.sleep` to prevent retry delays
- Ensure mock data won't trigger infinite loops (e.g., pagination 'last' values)
- Use `isinstance(obj, list)` not `isinstance(obj, list[Type])` (parameterized generics fail)
- Account for service-level transformations (e.g., `[:-1]` slicing)

---

## File & Module Naming

| Type        | Convention          | Example                |
| ----------- | ------------------- | ---------------------- |
| Module      | `snake_case/`       | `data_system/`         |
| Python file | `snake_case.py`     | `trade_repository.py`  |
| Model file  | `{entity}_model.py` | `bot_tick_model.py`    |
| Test file   | `test_{module}.py`  | `test_trade_model.py`  |
| Config file | `{context}_config.py` | `supabase_config.py` |
| Script file | `{action}_{target}.py` | `fetch_trades.py`    |

### Module Exports (`__init__.py`)

Export the public API explicitly. Only export what external consumers need:

```python
# ✅ Correct - Export public domain models and interfaces
from .models.bot_model import Bot
from .models.trade_model import Trade
from .repositories.bot_repository import BotRepository
```

**What NOT to export:**
- Internal utilities used only within the module
- Implementation details (e.g., services in a connector/service/client architecture)
- Helper functions that are module-internal

```python
# ❌ Wrong - Don't export internal utilities
from .internal_utils import get_nonce, sign_request  # Only used internally
```

**Rule of thumb:** If it's imported by code outside this module, it should be in `__init__.py`. If it's only used internally, don't export it.

### Scripts (`scalper/scripts/`)

Standalone scripts for local testing and manual operations live in `scalper/scripts/`. These are
entry points for testing implementations, not production code. Examples:

- `fetch_trades.py` — Fetch trade data from Kraken
- `run_backtest.py` — Run a backtest locally
- `start_scalping.py` — Start live trading

Scripts don't require unit tests but may require clear docstrings explaining usage.

#### Script Structure

Use **Click** for command-line interfaces:

```python
import click

@click.command()
@click.option('--pair', '-p', required=True, help='Trading pair (e.g. BTCGBP)')
@click.option('--start', '-s', required=True, help='Start timestamp (e.g. 2025-1-1-0-0-0)')
def fetch_trades(pair: str, start: str) -> None:
    '''Fetch trades from the exchange and store locally.'''
    # Implementation...

if __name__ == '__main__':
    fetch_trades()
```

#### Script Conventions

- **CLI with Click** — Use `@click.command()` and `@click.option()` for arguments
- **Short flags** — Provide `-p` style shortcuts for common options
- **Helper functions** — Extract logic into helper functions for readability
- **Entry point guard** — Always use `if __name__ == '__main__':`

For complex scripts, break into helper functions:

```python
@click.command()
@click.option('--pair', '-p', required=True)
def run_backtest(pair: str) -> None:
    '''Run a backtest on the specified trading pair.'''
    engine = create_engine(pair)
    results = engine.run()
    output_results(results)


def create_engine(pair: str) -> BacktestingEngine:
    '''Create a backtesting engine with default configuration.'''
    # Setup logic...


def output_results(results: pd.DataFrame) -> None:
    '''Display and plot backtest results.'''
    # Output logic...
```

---

## Configuration

### Environment Variables

**Application entry points** load `.env` once:

```python
from utils import load_env, LOG_FORMAT

load_env()  # MUST be called before importing modules that use env vars
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

# Import modules that depend on env vars AFTER load_env()
from data_system import SupabaseClient
```

**⚠️ Critical:** Call `load_env()` **before** importing modules that read env vars at import time (e.g., `SupabaseConfig`). Otherwise env vars won't be loaded yet!

**Library code** uses `os.getenv()` directly:

```python
import os

class SupabaseConfig:
    URL = os.getenv('SUPABASE_URL')
    KEY = os.getenv('SUPABASE_KEY')
```

**Production:** Environment variables come from AWS/platform, no `.env` file needed.

### Config Classes

Configuration classes are simple containers with class attributes:

```python
class LocalSQLiteConfig:
    LOCAL_STORAGE_PATH = ROOT_DIR / 'scalper' / 'local_storage'
    SCALPER_DB_URL = f'sqlite:///{LOCAL_STORAGE_PATH / "scalper.db"}'
```

### Logging

- **Never** call `logging.basicConfig()` in library/service code
- Configure logging **only at application entry points** (scripts, main modules)
- Services should use `logger = logging.getLogger(__name__)` and log without configuration

**Rationale:** Library code shouldn't control application-wide logging config. Multiple calls to `basicConfig()` can cause conflicts.

---

# Part 2: Architectural Patterns

These patterns apply **when relevant**. Not all modules need all patterns.

---

## Repository Pattern

**When to use:** Modules that need data access with potential for multiple backends.

**Example:** Data System uses repositories to abstract SQLAlchemy vs Supabase.

### Structure

Separate interfaces from implementations:

1. **Base Repository (Interface):** Abstract base class defining the contract
2. **Specific Repository (Implementation):** Concrete class for a specific backend

```python
# Interface
class TradeRepository(ABC):
    @abstractmethod
    def add(self, trades: list[Trade]) -> None:
        pass

# Implementation
class SQLAlchemyTradeRepository(TradeRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, trades: list[Trade]) -> None:
        # Implementation details...
```

### Naming Convention

`{Backend}{Entity}Repository` — e.g., `SupabaseBotRepository`, `SQLAlchemyTradeRepository`

### File Structure

```
repositories/
└── entity/
    ├── entity_repository.py           # Abstract base class
    └── backend_entity_repository.py   # Concrete implementation
```

---

## Dependency Injection

**When to use:** Classes that depend on external services (databases, APIs, clients).

Inject dependencies rather than instantiating them internally:

```python
# Correct
def __init__(self, client: SQLAlchemyClient) -> None:
    self.client = client

# Wrong - don't do this
def __init__(self) -> None:
    self.client = SQLAlchemyClient()
```

---

## Client Abstraction

**When to use:** Wrapping third-party SDKs or managing database connections.

### Context Manager Pattern

For transaction-based clients (e.g., SQLAlchemy):

```python
@contextmanager
def session(self) -> Generator[Session, None, None]:
    session = self.SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

### Proxy Pattern

For delegating to underlying clients (e.g., Supabase):

```python
class SupabaseClient:
    def __init__(self) -> None:
        self._client = create_client(SupabaseConfig.URL, SupabaseConfig.KEY)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
```

---

## Layered Architecture (Client/Service/Connector)

**When to use:** Modules that interact with external APIs or services requiring retry logic, authentication, and domain transformation.

**Example:** Exchange Connector uses this pattern for Kraken API integration.

### Three-Layer Structure

1. **Client layer** — Low-level HTTP/network concerns, error parsing, authentication
2. **Service layer** — Business logic, retry mechanisms, pagination, validation  
3. **Connector layer** — Public API, domain object transformation, high-level interface

### Multi-Exchange Support

The Exchange Connector module is designed for **future multi-exchange support** (Binance, Coinbase, etc.).

**Key architectural decisions:**
- **Connectors** are the public API and must be platform-agnostic
- **Services** are platform-specific (Kraken-specific currently)
- **Consumers** always import connectors, never services directly

**Current structure:**
```python
from exchange_connector import TickerConnector  # ✅ Correct (public API)
from exchange_connector.services import TickerService  # ❌ Wrong (internal)
```

**Future structure when adding new exchanges:**
```
exchange_connector/
├── __init__.py              # Exports connectors only
├── connectors/              # Platform-agnostic interfaces (public)
│   ├── ticker_connector.py  # Routes to platform-specific service
│   └── ...
├── api/                     # Platform-specific API clients (internal)
│   ├── kraken_api_client.py
│   └── binance_api_client.py
└── services/                # Platform-specific services (internal)
    ├── kraken/
    │   └── ticker_service.py
    └── binance/
        └── ticker_service.py
```

### Layer Responsibilities

**Connector layer (domain logic):**
- Transform API responses to domain objects (`Trade`, etc.)
- Validate business rules (order constraints, balance checks)
- Provide consistent interface across exchanges
- Handle domain-specific caching or enrichment

**Service layer (platform logic):**
- Handle platform-specific API details
- Implement retry/rate-limiting strategies
- Manage pagination for large datasets
- Parse platform-specific error codes

**Client layer (network/auth):**
- Low-level HTTP requests
- Authentication and signing
- Parse HTTP-level errors

### Key Principles

**Error handling belongs in the layer that can handle it:**
```python
# Client handles its own errors
class KrakenApiClient:
    def make_request(self, method: str, endpoint: str, params: dict) -> dict:
        response = self._do_request(method, endpoint, params)
        self._handle_errors(response)  # Internal responsibility
        return response

# Service focuses on business logic
class KrakenService:
    @retry(...)  # Retry on rate limits
    def make_request(self, method: str, endpoint: str, params: dict) -> dict:
        response = self.client.make_request(method, endpoint, params)
        return response['result']  # Extract result, errors already handled
```

**Validate at boundaries where external data enters:**
```python
class TradesConnector:
    def _to_domain(self, raw_data: list) -> list[Trade]:
        '''Convert raw API data to domain objects with validation.'''
        results = []
        for item in raw_data:
            try:
                if len(item) < 7:
                    raise ValueError(f'Incomplete data: expected 7 fields')
                results.append(Trade(...))
            except (ValueError, IndexError, TypeError) as e:
                raise ValueError(f'Failed to parse: {item}. Error: {e}')
        return results
```

**Add layers only when they provide value:**
- ✅ Domain transformation (raw API → typed objects)  
- ✅ Business logic (validation, calculations)  
- ✅ Retry/resilience patterns  
- ❌ Simple delegation with no transformation

**Connector layer is strategic, not just tactical:**
- Even if a connector currently only delegates to a service, it provides value by:
  - Establishing a platform-agnostic interface for future exchanges
  - Providing a stable public API separate from internal implementation
  - Creating a natural home for domain logic as it emerges
- Keep connectors thin but present — they enable future extensibility

**Question to ask:** "What does this layer add beyond passing data through?"
- For services: Platform-specific logic, retry, pagination
- For connectors: Domain transformation, multi-exchange abstraction


---

## Layered Module Structure

**When to use:** Complex modules with multiple concerns (data, config, logic).

```
module_name/
├── __init__.py          # Public API exports
├── models/              # Immutable dataclasses
├── config/              # Environment/settings classes
├── clients/             # Low-level connectivity
└── repositories/        # Business logic / CRUD
```

Simpler modules may only need a flat structure with a few files.

---

# Part 3: Domain Knowledge

Trading-specific conventions for this project.

---

## Trading Pairs

- Use Kraken format: `XXBTZGBP`, `XETHZUSD`
- Always store in Kraken format for consistency

## Bot IDs

Human-readable format: `{asset}_{interval}_{version}`

- Examples: `btc_1m_001`, `eth_5m_v2`

## Signals vs Sides

- **Signals:** `buy`, `hold`, `sell` — Strategy decisions
- **Sides:** `buy`, `sell` — Order execution
- **Legacy sides:** `b`, `s` — Kraken API format for historical trades

---

# Part 4: Database Conventions

Apply when working with database schemas or models that map to tables.

---

## Naming

- **Tables:** Plural, snake_case (`bot_ticks`, `bot_orders`)
- **Columns:** Singular, snake_case (`balance_base`, `created_at`)
- **Primary keys:** `id` (or component names for composite keys)
- **Foreign keys:** `{referenced_table_singular}_id` (e.g., `bot_id`, `run_id`)

## Type Mapping

| Python Type | PostgreSQL       | SQLite      |
| ----------- | ---------------- | ----------- |
| `str`       | `TEXT`           | `TEXT`      |
| `int`       | `INTEGER/BIGINT` | `INTEGER`   |
| `float`     | `FLOAT/DECIMAL`  | `REAL`      |
| `datetime`  | `TIMESTAMPTZ`    | N/A         |
| `UUID`      | `UUID`           | N/A         |
| `dict`      | `JSONB`          | N/A         |
| `Decimal`   | `DECIMAL(32,12)` | N/A         |

## Constraints

- Use `CHECK` constraints for enum-like fields
- Use `ON DELETE CASCADE` for child tables
- Add indexes for common query patterns
- Document composite primary keys in model docstrings

---

# Checklists

## New Feature Checklist

- [ ] Models are frozen dataclasses with full docstrings
- [ ] All methods have type hints
- [ ] Tests use Given/When/Then structure
- [ ] Tests have appropriate pytest markers
- [ ] Markers registered in `pytest.ini`
- [ ] Makefile target added for new module tests
- [ ] Public API exported in `__init__.py`

## Repository Pattern Checklist (when applicable)

- [ ] Abstract base class defines the interface
- [ ] Implementation injected with client (dependency injection)
- [ ] Naming follows `{Backend}{Entity}Repository`
- [ ] Both interface and implementation exported

---

**Module Auditing:** See `.github/prompts/audit-module.prompt.md` for the comprehensive audit checklist.
