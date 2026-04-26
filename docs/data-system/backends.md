# Backends

The system uses two distinct database backends optimised for their respective use cases.

## Dual Schema Architecture

| Backend              | Engine     | Purpose                          | Tables                                        |
| -------------------- | ---------- | -------------------------------- | --------------------------------------------- |
| **Local SQLite**     | SQLAlchemy | Backtesting, optimisation & jobs | `trades`, `generalisation_evaluation`, `jobs` |
| **Cloud PostgreSQL** | Supabase   | Live trading & audit trails      | `bots`, `bot_runs`, `bot_ticks`, `bot_orders` |

**Rationale:**

- **SQLite** is lightweight and requires no infrastructure - ideal for rapid local experimentation.
- **PostgreSQL/Supabase** provides cloud-native durability, real-time access, and integrates
  with the live-trading process running on Fly.io.

## Client Patterns

The two clients expose different APIs suited to their underlying technologies.

### SQLAlchemyClient

Exposes a **session context manager** for transaction safety:

```python
with client.session() as session:
    session.execute(...)  # Auto-commits on success, rolls back on error
```

### SupabaseClient

Uses the **proxy pattern** to delegate all method calls to the underlying Supabase client:

```python
client = SupabaseClient()  # Handles config internally
client.table("bots").select("*").execute()  # Direct access to Supabase API
```

> **Note:** The proxy pattern provides simpler instantiation but means IDE autocomplete and type
> checking are not available for delegated methods on `SupabaseClient`.

## Environment Configuration

| Config Class        | Source                                                                                      | Usage                         |
| ------------------- | ------------------------------------------------------------------------------------------- | ----------------------------- |
| `LocalSQLiteConfig` | Hardcoded paths                                                                             | Local development/backtesting |
| `SupabaseConfig`    | Environment variables (`SUPABASE_URL`, `SUPABASE_KEY`) read lazily via metaclass properties | Cloud deployment              |

> **Note:** `SupabaseConfig` reads env vars at attribute access time (not import time) using
> metaclass `@property`. This means scripts can import `data_system` in normal import order without
> needing to call `load_env()` before the import statement.
