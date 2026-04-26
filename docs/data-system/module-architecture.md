# Module Architecture

The data system implements the **Repository Pattern** to decouple application logic from the
underlying database technologies. This architecture allows the system to remain agnostic to _where_
the data is stored.

## Layer Breakdown

The module is organised into four distinct layers:

| Layer            | Responsibility                                                                               |
| ---------------- | -------------------------------------------------------------------------------------------- |
| **Models**       | **Data structure** - Contains typed dataclasses.                                             |
| **Config**       | **Environment settings** - Handles credentials, URLs, and database paths.                    |
| **Clients**      | **Connectivity** - Handles low-level connections; _"How do we talk to the DB?"_.             |
| **Repositories** | **Logic** - Handles CRUD operations and business queries; _"What does the app want to do?"_. |

## The Repository Pattern in Practice

To achieve backend interchangeability (e.g., swapping SQLAlchemy for Supabase), the repo layer
utilises a strict separation between **Interfaces** and **Implementations**:

1. **Base Repositories _(The Interface)_:** We expose an abstract base class for each table. This
   acts as a _"contract"_, defining what methods are available (e.g.,
   `TradeRepository.get(pair, start, end)`) without defining how they work. Consumers of the
   data system rely solely on these base classes.

2. **Specific Repositories _(The Implementation)_:** These classes implement the Base Repository
   using a specific **Client**. For example, a `SQLAlchemyTradeRepository` implements the
   `TradeRepository` interface using the SQLAlchemy client.

## Benefits

1. **Decoupling:** Consumers can ask for a `TradeRepository` without caring if the underlying
   implementation is local (SQLAlchemy) or cloud-based (Supabase).

2. **Testability:** We can easily inject mock repositories or in-memory databases for testing
   without changing application logic.

3. **Flexibility:** Database backends can be swapped or migrated without impacting trading logic.

> _Today I store trades in PostgreSQL, tomorrow in Supabase, next week in DuckDB!_

## Getting Started

Here's how to wire up the data system in consuming code:

```python
# For local backtesting (SQLAlchemy/SQLite)
from data_system import SQLAlchemyClient, SQLAlchemyTradeRepository

client = SQLAlchemyClient()
trade_repo = SQLAlchemyTradeRepository(client)

# Fetch trades for backtesting
trades = trade_repo.get(pair='XXBTZGBP', start=1704067200.0, end=1704153600.0)
```

```python
# For live trading (Supabase/PostgreSQL)
from data_system import SupabaseClient, SupabaseBotRepository, SupabaseBotRunRepository

client = SupabaseClient()
bot_repo = SupabaseBotRepository(client)
run_repo = SupabaseBotRunRepository(client)

# Create a bot and start a run
bot = bot_repo.get('btc_1m_v1')
run = run_repo.add(BotRun(bot_id=bot.id))
```
