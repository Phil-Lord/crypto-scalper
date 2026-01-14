-- PostgreSQL Schema for Live Trading Tables --

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
    id BIGSERIAL PRIMARY KEY,                     -- Matches BotTick.id (int)

    -- Identifiers
    bot_id TEXT NOT NULL REFERENCES bots(id),     -- Denormalized for faster filtering
    run_id UUID NOT NULL REFERENCES bot_runs(id) ON DELETE CASCADE,

    -- Time Series Data
    timestamp TIMESTAMPTZ NOT NULL,               -- Matches BotTick.timestamp (The Heartbeat)

    -- Post-interval Portfolio State
    balance_base DECIMAL(32, 12) NOT NULL,        -- Matches BotTick.balance_base
    balance_quote DECIMAL(32, 12) NOT NULL,       -- Matches BotTick.balance_quote

    -- Market State
    price DECIMAL(32, 12) NOT NULL,               -- Matches BotTick.price
    signal TEXT NOT NULL,                         -- Matches BotTick.signal ('buy', 'sell', 'hold')

    -- Order Execution Details
    order_executed BOOLEAN NOT NULL DEFAULT FALSE,
    executed_at TIMESTAMPTZ,                      -- Nullable
    execution_price DECIMAL(32, 12),              -- Nullable
    execution_volume DECIMAL(32, 12),             -- Nullable (Note: Mapped float -> Decimal for safety)
    execution_fee DECIMAL(32, 12),                -- Nullable

    -- Error Information
    error TEXT,                                   -- Matches BotTick.error

    -- Constraints
    CONSTRAINT chk_signal CHECK (signal IN ('buy', 'sell', 'hold'))
);

-- Critical Index: Makes loading charts ("Select all ticks for this run") instant
CREATE INDEX idx_bot_ticks_run_time ON bot_ticks (run_id, timestamp ASC);

-- Optional Index: Helps debug by quickly finding rows where errors occurred
CREATE INDEX idx_bot_ticks_errors ON bot_ticks (id) WHERE error IS NOT NULL;
