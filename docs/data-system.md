# Data System

This is the storage module for the system, it defines database configurations/models and provides
data access services for other modules. It uses a multi-backend architecture as we need to support
different database tools and management services, namely:

- **SQLAlchemy** for local backtesting tables, e.g. `trades` and `generalisation_evaluation`.
- **Supabase** for live trading tables, e.g. `bots`, `bot_runs`, and `bot_ticks`.

## Module Architecture

The data system implements the **Repository Pattern** to decouple application logic from the
underlying database technologies. This architecture allows the system to remain agnostic to _where_
the data is stored.

### Layer Breakdown

The module is organised into four distinct layers:

| Layer            | Responsibility                                                                               |
| ---------------- | -------------------------------------------------------------------------------------------- |
| **Models**       | **Data structure** - Contains ORM definitions and typed dataclasses.                         |
| **Config**       | **Environment settings** - Handles credentials, URLs, and database paths.                    |
| **Clients**      | **Connectivity** - Handles low-level connections; _"How do we talk to the DB?"_.             |
| **Repositories** | **Logic** - Handles CRUD operations and business queries; _"What does the app want to do?"_. |

### The Repository Pattern in Practice

To achieve backend interchangeability (e.g., swapping SQLAlchemy for Supabase), the repo layer
utilises a strict separation between **Interfaces** and **Implementations**:

1. **Base Repositories _(The Interface)_:** We expose an abstract base class for each table. This
   acts as a _"contract"_, defining what methods are available (e.g., `get_trade_by_id`) without
   defining how they work. Consumers of the data system rely solely on these base classes.

2. **Specific Repositories _(The Implementation)_:** These classes implement the Base Repository
   using a specific **Client**. For example, a `SqlAlchemyTradeRepository` implements the
   `TradeRepository` interface using the SQLAlchemy client.

### Repository Pattern Benefits

1. **Decoupling:** Consumers can ask for a `TradeRepository` without caring if the underlying
   implementation is local (SQLAlchemy) or cloud-based (Supabase).

2. **Testability:** We can easily inject mock repositories or in-memory databases for testing
   without changing application logic.

3. **Flexibility:** Database backends can be swapped or migrated without impacting trading logic.

> _Today I store trades in PostgreSQL, tomorrow in Supabase, next week in DuckDB!_
