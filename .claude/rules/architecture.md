# Architecture Patterns

Reference for the architectural patterns used in this project. These apply **when relevant** —
not every module needs every pattern. Universal style rules live in `CLAUDE.md`.

---

## Repository pattern

Use when a module needs data access with potential for multiple backends. Data System uses this
to abstract SQLAlchemy (local SQLite) vs Supabase (cloud Postgres).

**Structure:**

```
repositories/
└── entity/
    ├── entity_repository.py            # Abstract base class (interface)
    └── backend_entity_repository.py    # Concrete implementation
```

```python
class TradeRepository(ABC):
    @abstractmethod
    def add(self, trades: list[Trade]) -> None: ...


class SQLAlchemyTradeRepository(TradeRepository):
    def __init__(self, client: SQLAlchemyClient) -> None:
        self.client = client

    def add(self, trades: list[Trade]) -> None:
        ...
```

**Naming:** `{Backend}{Entity}Repository` — e.g. `SupabaseBotRepository`,
`SQLAlchemyTradeRepository`. Both interface and implementations are exported from the module's
`__init__.py`.

---

## Dependency injection

Inject external dependencies (clients, repositories, exchange APIs) rather than instantiating
them internally:

```python
# ✅ Correct
def __init__(self, client: SQLAlchemyClient) -> None:
    self.client = client

# ❌ Wrong
def __init__(self) -> None:
    self.client = SQLAlchemyClient()
```

This makes the unit harder to use accidentally (you have to pass the right thing) and trivial to
test (pass a mock).

---

## Client abstraction

Wrap third-party SDKs and database connections in a project-owned client so call sites depend on
a stable interface.

**Context-manager pattern** for transactional clients (e.g. SQLAlchemy):

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

**Proxy pattern** for SDKs whose surface we want to forward unchanged (e.g. Supabase):

```python
class SupabaseClient:
    def __init__(self) -> None:
        self._client = create_client(SupabaseConfig.URL, SupabaseConfig.KEY)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)
```

---

## Layered architecture (Client / Service / Connector)

Use when a module talks to an external API needing retry, auth, and domain transformation. The
exchange connector follows this for Kraken.

**Three layers:**

1. **Client** — Low-level HTTP/network, error parsing, authentication.
2. **Service** — Business logic, retry, pagination, platform-specific error handling. Currently
   Kraken-specific.
3. **Connector** — Public API, domain object transformation, platform-agnostic interface.

**Public consumers always import connectors, never services directly:**

```python
from exchange_connector import TickerConnector       # ✅ Public API
from exchange_connector.services import TickerService  # ❌ Internal
```

**Layer responsibilities:**

| Layer     | Responsibility                                                                  |
|-----------|---------------------------------------------------------------------------------|
| Connector | Transform raw API → domain objects; validate business rules; multi-exchange API |
| Service   | Platform-specific HTTP shape; retry/rate-limit; pagination; error parsing       |
| Client    | Low-level requests, signing, HTTP-level errors                                  |

**Error handling belongs in the layer that can fix it.** Don't leak HTTP errors past the client;
don't leak retry logic past the service.

```python
class KrakenApiClient:
    def make_request(self, method, endpoint, params):
        response = self._do_request(method, endpoint, params)
        self._handle_errors(response)  # Client owns this
        return response


class KrakenService:
    @retry(...)  # Service owns retry policy
    def make_request(self, method, endpoint, params):
        response = self.client.make_request(method, endpoint, params)
        return response['result']  # Errors already handled below
```

**Validate at boundaries** where external data enters:

```python
class TradesConnector:
    def _to_domain(self, raw: list) -> list[Trade]:
        results = []
        for item in raw:
            try:
                if len(item) < 7:
                    raise ValueError(f'Incomplete data: expected 7 fields')
                results.append(Trade(...))
            except (ValueError, IndexError, TypeError) as e:
                raise ValueError(f'Failed to parse: {item}. Error: {e}')
        return results
```

**Add layers only when they earn their keep.** "What does this layer add beyond passing data
through?" If the answer is nothing, remove or merge it. Connectors are the exception — even thin
ones provide value as a stable, platform-agnostic public surface.

---

## Dual implementations (live + vectorised)

Strategies and indicators in `strategy_manager` have both:

- A **stateful, live** implementation called once per bar (`_generate_signal`, `update`)
- A **vectorised** implementation called with the full DataFrame for backtesting
  (`_generate_signals`, `compute`)

**Rule:** both implementations must produce identical output for identical data. Any logic
change must update both paths and have a test that runs them side-by-side.

```python
def _generate_signal(self, rule_results: dict) -> Signal:
    return rule_results['my_rule']

def _generate_signals(self, results: pd.DataFrame) -> pd.Series:
    return results['my_rule']
```

---

## Configuration

**Entry points** load `.env` once before importing modules that read env vars:

```python
from utils import LOG_FORMAT, load_env

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
```

**Library code** reads env vars lazily via metaclass properties so values resolve at access
time, not import time:

```python
class _SupabaseConfigMeta(type):
    @property
    def URL(cls) -> str | None:
        return os.getenv('SUPABASE_URL')

    @property
    def KEY(cls) -> str | None:
        return os.getenv('SUPABASE_KEY')


class SupabaseConfig(metaclass=_SupabaseConfigMeta):
    pass
```

Scripts can `import data_system` in normal order without worrying about whether `load_env()`
has run yet — config values are read at the point of use.

In production (Fly.io), env vars come from the platform; `load_env()` is a no-op.

---

## Memory management for long-running processes

Live trading runs 24/7. Anything that accumulates state must be bounded.

```python
from collections import deque

class SmaIndicator:
    def __init__(self, window: int):
        self.window = window
        self.prices = deque(maxlen=window)  # ✅ Drops oldest automatically

    def update(self, price: float) -> float | None:
        self.prices.append(price)
        if len(self.prices) < self.window:
            return None
        return sum(self.prices) / self.window
```

❌ Anti-pattern: `self.prices = []` — grows forever while only the last `window` values are
used.

Store only what you need: running averages over full history, window-sized buffers for rolling
calculations, clear intermediates after processing.

---

## Module exports — `__init__.py`

Export the **public API** explicitly. Only what external consumers need.

```python
# ✅ Correct
from .models.bot_model import Bot
from .repositories.bot_repository import BotRepository

# ❌ Wrong — internal helper
from .internal_utils import get_nonce
```

Rule of thumb: if it's imported by code outside this module, it goes in `__init__.py`. If it's
only used internally, leave it out.
