# Architecture Decision Log

This document captures important architectural decisions (ADs) and their context and consequences.
This is primarily so I don't forget **_why_** I did something.

## System-wide Decisions

### Datetime Precision

#### Decision

- The Python `datetime` type is precise enough for timestamps.

#### Reasoning

- `datetime` is precise to the microsecond ($10^{-6}$ seconds).
- For example, 12:00:00.123456 (resolves to 0.000001 seconds).
- PostgreSQL `TIMESTAMPTZ` also resolves to microseconds by default, making a 1:1 map.
- We will be limited by the speed of light (internet latency), not timestamp precision.

### Timestamp Type

#### Decision

- We should store timestamps as Timezone-Aware UTC `datetime` objects in code and database.

#### Reasoning

- The 3 AM Test - If the bot crashes, copying 1735689600 into a converter is unideal.
- SQL DBs, including PostgreSQL, have powerful time-based functions for TIMESTAMP columns.
- Python's `datetime` objects can be "aware" (contain timezone info), `float`/`int` cannot.

## Data System Decisions

## Trade Executor Decisions

## Backtesting Engine Decisions
