# Cloud Architecture

This section documents key design decisions made during the development of the cloud architecture
for the scalper. It captures the reasoning, trade-offs, and examples for future reference.

## Execution Model

As opposed to a constant loop running in a VM or something, the scalper runs one self-contained
trading cycle per execution. This has several advantages:

- Each decision is computed independently based on market data and persisted state.
- High fault tolerance - a failure in one interval does not affect the next.
- Each run is isolated, reducing long-running state or memory issues.
- Simple scaling/parallelisation, logging, and retry logic.
- More cost efficient - No paying for idle loops.

## Compute Service

AWS Lambda is used as the compute environment, triggered every interval by Amazon EventBridge
Scheduler. This provides simple, managed cron-style scheduling without wasting compute resources or
necessitating manual uptime management. Here's the flow:

EventBridge → Lambda → [TradeExecutor](trade-executor.md) → runs 1 interval + maybe executes trade.

## Database

Supabase (Postgres) stores trading data integrating seemlessly with AWS. The free tier
(500 MB database, 500 MB RAM, shared CPU) is sufficient for the current usage, and simple API and
SQL access is provided for both analytics and scalper storage.

The `interval_results` table is used to store results following each live trading interval. The
client configuration and service for the table is stored within the [Data System](data-system.md) module. For
each interval, the [TradeExecutor](trade-executor.md) instance uses its [IntervalContext](trade-executor.md#interval-context-object)
to load any required state from the `interval_results` table before running the strategy and save
its results afterwards. The table below shows the fields for the `interval_results` table.

| Column             | Description                            | Type                       |
| ------------------ | -------------------------------------- | -------------------------- |
| `id`               | UUID or serial PK                      | uuid / bigint              |
| `bot_id`           | Unique identifier for the bot instance | text                       |
| `timestamp`        | UTC interval start timestamp           | timestamp (with time zone) |
| `strategy_name`    | Strategy name                          | text                       |
| `pair`             | Trading pair (e.g., BTC/GBP)           | text                       |
| `price`            | Market price used                      | decimal                    |
| `signal`           | 'buy' / 'sell' / 'hold'                | text                       |
| `base_balance`     | At start or end of interval            | decimal                    |
| `quote_balance`    | Same                                   | decimal                    |
| `order_executed`   | Bool                                   | boolean                    |
| `execution_price`  | Nullable                               | decimal (nullable)         |
| `execution_volume` | Nullable                               | decimal (nullable)         |
| `notes`            | Optional diagnostic text               | text (nullable)            |

To enable the running of multiple scalper instances concurrently, we use a uniqueness constraint
on the `bot_id` and `timestamp` fields. This prevents race conditions where the same bot writes
two rows for the same timestamp. The `bot_id` format is PAIR_INTERVAL_VERSION, i.e. `btc_1m_v1`.
This format is predictable and makes querying easy, for example:

```sql
-- It's easy to select by human-readable bot_id:
SELECT * FROM interval_results WHERE bot_id='btc_1m_v1'

-- We can compare bots by strategy:
SELECT * FROM interval_results
WHERE bot_id LIKE 'btc_%'
AND strategy_name = 'PrecisionTrend'

-- We can compare bots for a specific coin and interval:
SELECT * FROM interval_results WHERE bot_id LIKE 'btc_1m_%'
```

## Container-based Deployment

The Lambda function is deployed as a Docker container hosted in Amazon Elastic Container Registry
(ECR). Using container-based deployment ensures compatibility with the project's structure as
there's no need to flatten dependencies or zip modules. This also enables consistent runtime
environments between local development and production. Finally, containers provide portability for
switching to other cloud platforms if necessary in the future.

## Logging

- Structured logging in JSON to integrate with CloudWatch.
- External logging sink (e.g., Supabase, S3, or Datadog) for long-term trade audit trails.
- Include Lambda’s request_id or interval timestamp in every log line for traceability.

## Infrastructure as Code

Terraform is used to manage all cloud resources. This makes it easy to manage environment changes,
redeployments, and infrastructure version control.
