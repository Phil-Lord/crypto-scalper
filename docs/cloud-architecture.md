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
necessitating manual uptime management.

## Database

Supabase (Postgres) stores trading data integrating seemlessly with AWS. The free tier
(500 MB database, 500 MB RAM, shared CPU) is sufficient for the current usage, and simple API and
SQL access is provided for both analytics and scalper storage.

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
