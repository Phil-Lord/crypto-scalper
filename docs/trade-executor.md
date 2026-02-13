# Trade Executor

This section documents the technical decisions and implementation details of the Trade Executor.

## Interval Context Object

Serves as a state handler for context handoff between a Trade Executor object's intervals. While
each Lambda invocation is stateless, the trading logic depends on a persisted state containing
things like open positions, wallet balances, and previous orders. Using an Interval Context object
enables the abstraction of the following actions from the Trade Executor:

- Fetching the latest position and last trade from the database at the start.
- Writing back the results and trade outcomes at the end.

This allows the TradeExecutor to accept a context instance and avoid maintaining local memory.

## TODO

- Trade decision idempotency: Avoid Lambda's automatic retry on error using a db logged UUID per
  interval run or a pair/timestamp check before execution.
- Refine volume handling: Rather than trading the whole wallet.
- Update logging to use JSON for Cloudwatch and Supabase/S3/Datadog external sink. Include Lambda’s
  request_id or interval timestamp in every log line for traceability.
- Error handling: “Insufficient funds”, “Invalid order size”, “Rate limit exceeded”, coding bugs,
  network errors, etc.
- Terraform & Deployment Improvements: Define environment variables in Terraform, referencing AWS
  Secrets Manager ARNs. Use Lambda container image size optimisation (e.g.,
  base image public.ecr.aws/lambda/python:3.11). Keep Supabase credentials encrypted via Secrets
  Manager, not plaintext env vars.
