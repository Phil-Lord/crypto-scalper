# Data System

This is the storage module for the system, it defines database configurations/models and provides
data access services for other modules. It uses a multi-backend architecture as we need to support
different database tools and management services, namely:

- **SQLAlchemy** for local backtesting tables, e.g. `trades` and `generalisation_evaluation`.
- **Supabase** for live trading tables, e.g. `bots`, `bot_runs`, and `bot_ticks`.

## Contents

| Page                                          | Description                                           |
| --------------------------------------------- | ----------------------------------------------------- |
| [Module Architecture](module-architecture.md) | Repository pattern and layer breakdown                |
| [Backends](backends.md)                       | Dual schema architecture, clients, and configuration  |
| [Schema Reference](schema-reference.md)       | Table definitions, indexes, and integrity constraints |
