# Data System

This is the storage module for the system, it defines database configurations/models and provides
data access services for other modules. It uses a multi-backend architecture as we need to support
different database tools and management services, namely:

- SQLAlchemy for the `trades` table, which stores historic trade data for backtesting.
- Supabase for the `interval_results` table, which stores live trading results.

## Module Structure

### `clients/` - Raw database clients

- `base_client.py`: Abstract base class definition.
- `sqlalchemy_client.py`: Creates engine/session for SQLAlchemy.
- `supabase_client.py`: Holds the Supabase Python client and initialises connection.

### `services/` - Provide table-specific operations using clients

- `trades_service.py`: Uses SQLAlchemy client and Trades model.
- `interval_service.py`: Uses Supabase client.

### `models/` - ORM definitions and typed dataclasses for models

- `sqlalchemy/base.py`: ABC for ORM SQL Alchemy models.
- `sqlalchemy/trades_model.py`: ORM model for `trades` table.
- `supabase/interval_results_schema.py`: Schema descriptor dataclass for `interval_results` table.

### `config/` - Credentials, URLs, database paths, etc.

- `database_config.py`: Settings for SQL DB
- `supabase_config.py`: Settings for Supabase client
