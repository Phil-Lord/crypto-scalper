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

Supabase (PostgreSQL) stores all live trading data, integrating seamlessly with AWS Lambda. The
free tier (500 MB database, 500 MB RAM, shared CPU) is sufficient for current usage.

### Data Model

The live trading database follows a clear hierarchy:

```
bots (1) ──► bot_runs (many) ──► bot_ticks (many)
                              └─► bot_orders (many)
```

| Table        | Purpose                                                   |
| ------------ | --------------------------------------------------------- |
| `bots`       | Configuration identity (pair, strategy, version, params)  |
| `bot_runs`   | Execution sessions (when a bot is "turned on")            |
| `bot_ticks`  | Granular interval results (the immutable decision record) |
| `bot_orders` | Executed trades linked to their triggering tick           |

This separation provides:

- **Relational Integrity:** Query exactly which configuration produced which result.
- **Performance:** Indexed `run_id` lookups remain fast even with millions of ticks.
- **Data Deduplication:** Strategy name and pair stored once in `bots`, not every tick.

The `bot_id` format (`btc_1m_v1`) acts as **configuration-level identity**, while `run_id` provides
**execution session identity** - enabling bot reuse across restarts and long-term performance
tracking per configuration.

> For detailed schema definitions, indexes, and constraints, see the
> [Schema Reference](data-system/schema-reference.md) documentation.

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
