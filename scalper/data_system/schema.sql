-- ============================================================================
-- PostgreSQL Schema for Live Trading Tables --
-- ============================================================================

-- Table: bots
CREATE TABLE bots (
    id TEXT PRIMARY KEY,                          -- Matches Bot.id (human readable string)
    pair TEXT NOT NULL,                           -- Matches Bot.pair
    strategy_name TEXT NOT NULL,                  -- Matches Bot.strategy_name
    strategy_version TEXT NOT NULL,               -- Matches Bot.strategy_version
    interval INTEGER NOT NULL,                    -- Matches Bot.interval (in minutes)
    parameters JSONB NOT NULL,                    -- Matches Bot.parameters (dict -> jsonb)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW() -- Matches Bot.created_at
);


-- Table: bot_runs
CREATE TABLE bot_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), -- Matches BotRun.id
    bot_id TEXT NOT NULL REFERENCES bots(id) ON DELETE CASCADE, 
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Matches BotRun.started_at
    completed_at TIMESTAMPTZ                       -- Matches BotRun.completed_at (Nullable)
);

CREATE INDEX idx_bot_runs_bot_started ON bot_runs (bot_id, started_at DESC);


-- Table: bot_ticks
CREATE TABLE bot_ticks (
    -- Identifiers
    id BIGSERIAL PRIMARY KEY,                     -- Matches BotTick.id (int)
    bot_id TEXT NOT NULL REFERENCES bots(id),     -- Denormalized for faster filtering
    run_id UUID NOT NULL REFERENCES bot_runs(id) ON DELETE CASCADE,

    -- Tick Data
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), -- Matches BotTick.timestamp (The Heartbeat)
    price DECIMAL(32, 12) NOT NULL,               -- Matches BotTick.price
    signal TEXT NOT NULL,                         -- Matches BotTick.signal ('buy', 'sell', 'hold')
    error TEXT,                                   -- Matches BotTick.error

    -- Portfolio State
    balance_base DECIMAL(32, 12) NOT NULL,        -- Matches BotTick.balance_base
    balance_quote DECIMAL(32, 12) NOT NULL,       -- Matches BotTick.balance_quote

    CONSTRAINT chk_signal CHECK (signal IN ('buy', 'sell', 'hold'))
);

-- Critical Index: Makes loading charts ("Select all ticks for this run") instant
CREATE INDEX idx_bot_ticks_run_time ON bot_ticks (run_id, timestamp ASC);

-- Optional Index: Helps debug by quickly finding rows where errors occurred
CREATE INDEX idx_bot_ticks_errors ON bot_ticks (id) WHERE error IS NOT NULL;


-- Table: bot_orders
CREATE TABLE bot_orders (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Foreign Keys
    bot_id TEXT NOT NULL REFERENCES bots(id),
    run_id UUID NOT NULL REFERENCES bot_runs(id) ON DELETE CASCADE,
    tick_id BIGINT REFERENCES bot_ticks(id),

    -- Order Details
    exchange_order_id TEXT NOT NULL,
    side TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'placed',
    placed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Order Fill Details
    filled_at TIMESTAMPTZ,
    price DECIMAL(32, 12),
    volume DECIMAL(32, 12),
    fee DECIMAL(32, 12),

    CONSTRAINT chk_side CHECK (side IN ('buy', 'sell')),
    CONSTRAINT chk_status CHECK (status IN ('placed', 'filled', 'failed'))
);


-- ============================================================================
-- SQLite Schema for Backtesting Tables --
-- ============================================================================

-- Table: trades
-- Stores historical trade data fetched from Kraken API for backtesting.
CREATE TABLE trades (
    -- Composite Primary Key: trade_id is only unique per pair on Kraken
    trade_id BIGINT NOT NULL,       -- Matches Trade.trade_id (from Kraken API)
    pair TEXT NOT NULL,             -- Matches Trade.pair (e.g., 'XXBTZGBP')

    -- Trade Data
    price FLOAT NOT NULL,           -- Matches Trade.price
    volume FLOAT NOT NULL,          -- Matches Trade.volume
    timestamp FLOAT NOT NULL,       -- Matches Trade.timestamp (Unix seconds, sub-second precision)
    side TEXT NOT NULL,             -- Matches Trade.side ('b' = buy, 's' = sell)
    order_type TEXT NOT NULL,       -- Matches Trade.order_type ('m' = market, 'l' = limit)

    PRIMARY KEY (trade_id, pair)
);

-- Index: Optimises the most common query pattern (fetching trades for a pair within a time range)
CREATE INDEX ix_trades_pair_timestamp ON trades (pair, timestamp);

-- Index: Supports queries filtering by pair only (without time constraint)
CREATE INDEX ix_trades_pair ON trades (pair);


-- Table: out_of_sample_evaluation
-- Stores results of evaluating Optuna trial parameters across time windows.
CREATE TABLE out_of_sample_evaluation (
    study_name TEXT NOT NULL,               -- Matches OutOfSampleEvaluation.study_name
    trial_number INTEGER NOT NULL,          -- Matches OutOfSampleEvaluation.trial_number
    start_timestamp REAL NOT NULL,          -- Matches OutOfSampleEvaluation.start_timestamp
    end_timestamp REAL NOT NULL,            -- Matches OutOfSampleEvaluation.end_timestamp
    is_value REAL NOT NULL,                 -- Matches OutOfSampleEvaluation.is_value (Optuna objective value at evaluation time)
    oos_balance_ratio REAL NOT NULL,        -- Matches OutOfSampleEvaluation.oos_balance_ratio

    PRIMARY KEY (study_name, trial_number, start_timestamp, end_timestamp)
);


-- Table: jobs
-- Stores information about background jobs (e.g., get_trades, run_backtest).
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,                        -- Matches Job.id (UUID stored as text)
    job_type TEXT NOT NULL,                     -- Matches Job.job_type (e.g., 'get_trades', 'run_backtest')
    status TEXT NOT NULL DEFAULT 'pending',     -- Matches Job.status ('pending', 'running', 'done', 'error')
    message TEXT,                               -- Matches Job.message (optional status/error message)
    created_at REAL NOT NULL,                   -- Matches Job.created_at (Unix timestamp)
    updated_at REAL NOT NULL                    -- Matches Job.updated_at (Unix timestamp)
);