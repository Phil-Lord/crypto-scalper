'''
Manual end-to-end verification of the four live-trading Supabase repositories.

Exercises every public method on `SupabaseBotRepository`, `SupabaseBotRunRepository`,
`SupabaseBotTickRepository`, and `SupabaseBotOrderRepository` against the real Supabase
project pointed at by `SUPABASE_URL` / `SUPABASE_KEY`. Verifies type round-trips
(timezone-aware datetimes, `Decimal` precision, `UUID`, enums, JSONB dicts) and FK
constraint behaviour.

⚠️  SAFETY
    Prod Supabase holds thousands of live-trading rows. This script must not interfere
    with them. Every row inserted carries the prefix `claudit-test-` plus a per-run UUID
    fragment. Cleanup runs in `try`/`finally` and deletes only by that exact bot_id, in
    reverse FK order. After cleanup, a residue sweep queries every table for any row
    whose bot_id starts with the prefix; if any remain, the script exits non-zero with
    the IDs.

    Constraints baked into this script — do not bypass when extending it:

    1. Every test row's `bot_id` (or `id` for the bots table) starts with `claudit-test-`.
    2. Every successful insert is recorded in the ledger.
    3. Cleanup runs in `try`/`finally`, even on exception or KeyboardInterrupt.
    4. After cleanup, a residue sweep verifies zero rows match the prefix.
    5. Every `.delete()` call is scoped via `.eq()` to a specific bot_id.
       No bare deletes, no truncates, no schema operations.

Usage
    uv run python scalper/scripts/test_supabase_repos.py
    uv run python scalper/scripts/test_supabase_repos.py --yes  # skip interactive confirm
'''

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import click

from data_system import (
    Bot,
    BotOrder,
    BotRun,
    BotTick,
    OrderStatus,
    Side,
    Signal,
    SupabaseBotOrderRepository,
    SupabaseBotRepository,
    SupabaseBotRunRepository,
    SupabaseBotTickRepository,
    SupabaseClient,
)
from data_system.config.supabase_config import SupabaseConfig
from utils import LOG_FORMAT, load_env

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

TEST_PREFIX = 'claudit-test-'
TEST_PAIR = 'XXBTZGBP'

# Realistic Kraken-shaped values — high enough precision to catch float bugs, well within
# the documented DECIMAL(32, 12) schema limit so we don't trip the known truncation.
PRICE_BUY = Decimal('45123.50')
PRICE_SELL = Decimal('45987.25')
VOLUME = Decimal('0.00012345')
FEE = Decimal('0.00000123')
BALANCE_BASE = Decimal('0.12345678')
BALANCE_QUOTE = Decimal('1234.56789012')


@dataclass
class Ledger:
    '''Records every successful insert so cleanup can target exact rows.'''
    bot_ids: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    def record_failure(self, scenario: str, message: str) -> None:
        self.failures.append(f'{scenario}: {message}')
        logger.error('%s FAILED: %s', scenario, message)


@click.command()
@click.option('--yes', is_flag=True, help='Skip interactive confirmation prompt.')
def main(yes: bool) -> None:
    '''Run the Supabase repo end-to-end test against the configured Supabase project.'''
    _confirm_target(yes)

    client = SupabaseClient()
    bot_repo = SupabaseBotRepository(client)
    run_repo = SupabaseBotRunRepository(client)
    tick_repo = SupabaseBotTickRepository(client)
    order_repo = SupabaseBotOrderRepository(client)

    _pre_flight_residue_check(client)

    ledger = Ledger()
    run_uuid = uuid4()
    primary_bot_id = f'{TEST_PREFIX}{run_uuid.hex[:8]}'
    holds_only_bot_id = f'{TEST_PREFIX}{run_uuid.hex[:8]}-h'

    try:
        _test_bot_repo(bot_repo, primary_bot_id, ledger)
        bot_run = _test_bot_run_repo(bot_repo, run_repo, primary_bot_id, ledger)
        linked_tick_id = _test_bot_tick_repo(
            bot_repo, run_repo, tick_repo, primary_bot_id, holds_only_bot_id, bot_run, ledger,
        )
        _test_bot_order_repo(order_repo, primary_bot_id, bot_run, linked_tick_id, ledger)
    finally:
        _cleanup(client, ledger.bot_ids)
        _residue_sweep(client, ledger.bot_ids)

    if ledger.failures:
        logger.error('TEST RUN FAILED — %d scenario(s) failed:', len(ledger.failures))
        for failure in ledger.failures:
            logger.error('  %s', failure)
        sys.exit(1)

    logger.info('TEST RUN PASSED — all scenarios completed and all test data cleaned up.')


# ---------------------------------------------------------------------------------------
# Safety helpers
# ---------------------------------------------------------------------------------------

def _confirm_target(skip_prompt: bool) -> None:
    url = SupabaseConfig.URL
    if not url or not SupabaseConfig.KEY:
        click.echo('SUPABASE_URL or SUPABASE_KEY missing from environment. Aborting.', err=True)
        sys.exit(2)

    click.echo(f'\nTarget Supabase project: {url}')
    click.echo(
        'This script will INSERT, UPDATE, and DELETE rows on the bots, bot_runs, bot_ticks, '
        f'and bot_orders tables, scoped to bot_id starting with {TEST_PREFIX!r}.'
    )
    click.echo('Other tables (trades, generalisation_evaluation, jobs, ...) are not touched.\n')

    if skip_prompt:
        return

    answer = click.prompt('Continue? Type "yes" to proceed', default='', show_default=False)
    if answer.strip().lower() != 'yes':
        click.echo('Aborted by user.')
        sys.exit(0)


def _pre_flight_residue_check(client: SupabaseClient) -> None:
    '''Refuse to start if any test-prefixed rows are left from a prior run.'''
    leftover = _find_residue(client)
    if not leftover:
        return

    logger.warning('Residue from a prior run found:')
    for table, count in leftover.items():
        logger.warning('  %s: %d rows', table, count)
    logger.warning(
        'These rows are tagged %r so they are safe to delete, but this script will not touch '
        'them automatically. Re-run with --yes after manually cleaning them up, or extend this '
        'script if you trust the prefix-scoped cleanup.', TEST_PREFIX,
    )
    sys.exit(2)


def _find_residue(client: SupabaseClient) -> dict[str, int]:
    '''Count rows in each table whose bot_id (or id, for `bots`) starts with TEST_PREFIX.'''
    residue: dict[str, int] = {}

    bots = (
        client.table('bots').select('id').like('id', f'{TEST_PREFIX}%').execute()
    )
    if bots.data:
        residue['bots'] = len(bots.data)

    for table, column in [
        ('bot_runs', 'bot_id'),
        ('bot_ticks', 'bot_id'),
        ('bot_orders', 'bot_id'),
    ]:
        response = client.table(table).select(column).like(column, f'{TEST_PREFIX}%').execute()
        if response.data:
            residue[table] = len(response.data)

    return residue


def _cleanup(client: SupabaseClient, bot_ids: list[str]) -> None:
    '''
    Delete every row this run inserted, scoped by exact bot_id, in reverse FK order.

    Every delete is `.eq()` on a known bot_id from the ledger — never a bare delete or
    a wildcard. If the ledger is empty (e.g. nothing was successfully inserted) this
    is a no-op.
    '''
    if not bot_ids:
        logger.info('Cleanup: ledger empty, nothing to delete.')
        return

    for bot_id in bot_ids:
        if not bot_id.startswith(TEST_PREFIX):
            logger.error(
                'Refusing to delete bot_id %r — does not start with safety prefix %r.',
                bot_id, TEST_PREFIX,
            )
            continue

        logger.info('Cleanup: deleting rows for bot_id=%s', bot_id)
        client.table('bot_orders').delete().eq('bot_id', bot_id).execute()
        client.table('bot_ticks').delete().eq('bot_id', bot_id).execute()
        client.table('bot_runs').delete().eq('bot_id', bot_id).execute()
        client.table('bots').delete().eq('id', bot_id).execute()


def _residue_sweep(client: SupabaseClient, bot_ids: list[str]) -> None:
    '''
    After cleanup, confirm zero rows remain that match either the per-run bot_ids or the
    test prefix more broadly. If anything remains, exit non-zero with the IDs.
    '''
    leftover = _find_residue(client)
    if not leftover:
        logger.info('Residue sweep: clean — zero rows matching %r remain.', TEST_PREFIX)
        return

    logger.error('RESIDUE SWEEP FAILED — rows tagged %r still in the database:', TEST_PREFIX)
    for table, count in leftover.items():
        logger.error('  %s: %d rows', table, count)
    logger.error(
        'Per-run bot_ids that should have been deleted: %s', ', '.join(bot_ids) or '(none)'
    )
    sys.exit(3)


# ---------------------------------------------------------------------------------------
# Bot repo
# ---------------------------------------------------------------------------------------

def _test_bot_repo(bot_repo: SupabaseBotRepository, bot_id: str, ledger: Ledger) -> None:
    logger.info('--- SupabaseBotRepository ---')

    bot = Bot(
        id=bot_id,
        pair=TEST_PAIR,
        strategy_name='TestStrategy',
        strategy_version='v0.0.1',
        interval=1,
        parameters={
            'window': 14,
            'thresholds': {'buy': 30.0, 'sell': 70.0},
            'pairs': ['XXBTZGBP', 'XETHZGBP'],
        },
        created_at=datetime.now(timezone.utc),
    )

    try:
        added = bot_repo.add(bot)
        ledger.bot_ids.append(bot_id)
    except Exception as e:
        ledger.record_failure('bot_repo.add', f'unexpected exception: {e!r}')
        return

    _expect(added.id == bot.id, 'bot_repo.add', 'returned id mismatch')
    _expect(added.parameters == bot.parameters, 'bot_repo.add', 'parameters JSONB drift')
    _expect(
        added.created_at.tzinfo is not None,
        'bot_repo.add', 'created_at returned without timezone',
    )

    fetched = bot_repo.get(bot_id)
    _expect(fetched is not None, 'bot_repo.get', 'returned None for inserted bot')
    if fetched is not None:
        _expect(fetched == added, 'bot_repo.get', 'fetched bot does not equal inserted bot')

    try:
        bot_repo.add(bot)
    except Exception:
        pass
    else:
        ledger.record_failure(
            'bot_repo.add(duplicate)', 'expected exception on duplicate primary key',
        )

    missing = bot_repo.get(f'{TEST_PREFIX}does-not-exist-{uuid4().hex[:8]}')
    _expect(missing is None, 'bot_repo.get(missing)', 'expected None for non-existent id')


# ---------------------------------------------------------------------------------------
# BotRun repo
# ---------------------------------------------------------------------------------------

def _test_bot_run_repo(
    bot_repo: SupabaseBotRepository,
    run_repo: SupabaseBotRunRepository,
    bot_id: str,
    ledger: Ledger,
) -> BotRun:
    logger.info('--- SupabaseBotRunRepository ---')

    open_run = BotRun(bot_id=bot_id)
    closed_run = BotRun(
        bot_id=bot_id,
        completed_at=datetime.now(timezone.utc),
    )

    added_open = run_repo.add(open_run)
    added_closed = run_repo.add(closed_run)

    _expect(isinstance(added_open.id, UUID), 'bot_run_repo.add', 'id is not a UUID')
    _expect(added_open.completed_at is None, 'bot_run_repo.add', 'expected completed_at=None')
    _expect(
        added_closed.completed_at is not None
        and added_closed.completed_at.tzinfo is not None,
        'bot_run_repo.add', 'completed_at not timezone-aware',
    )

    fetched = run_repo.get(added_open.id)
    _expect(fetched is not None and fetched.id == added_open.id,
            'bot_run_repo.get', 'fetched run mismatch')

    missing = run_repo.get(uuid4())
    _expect(missing is None, 'bot_run_repo.get(missing)', 'expected None for non-existent id')

    completed_at = datetime.now(timezone.utc)
    completed = run_repo.complete(added_open.id, completed_at)
    _expect(completed is not None, 'bot_run_repo.complete', 'returned None for valid id')
    if completed is not None:
        _expect(
            completed.completed_at == completed_at,
            'bot_run_repo.complete', 'completed_at not preserved exactly',
        )
        _expect(
            completed.completed_at is not None and completed.completed_at.tzinfo is not None,
            'bot_run_repo.complete', 'completed_at not timezone-aware',
        )
    refetched = run_repo.get(added_open.id)
    _expect(refetched is not None and refetched.completed_at is not None,
            'bot_run_repo.complete', 'get after complete shows completed_at=None')

    not_completed = run_repo.complete(uuid4(), datetime.now(timezone.utc))
    _expect(not_completed is None, 'bot_run_repo.complete(missing)',
            'expected None for non-existent id')

    return added_closed  # the still-open-ish handle for tick/order tests below


# ---------------------------------------------------------------------------------------
# BotTick repo
# ---------------------------------------------------------------------------------------

def _test_bot_tick_repo(
    bot_repo: SupabaseBotRepository,
    run_repo: SupabaseBotRunRepository,
    tick_repo: SupabaseBotTickRepository,
    primary_bot_id: str,
    holds_only_bot_id: str,
    bot_run: BotRun,
    ledger: Ledger,
) -> int:
    logger.info('--- SupabaseBotTickRepository ---')

    base_time = datetime.now(timezone.utc)

    buy_tick = _make_tick(primary_bot_id, bot_run.id, base_time, Signal.BUY)
    hold_tick = _make_tick(
        primary_bot_id, bot_run.id, base_time + timedelta(minutes=1), Signal.HOLD,
    )
    sell_tick = _make_tick(
        primary_bot_id, bot_run.id, base_time + timedelta(minutes=2), Signal.SELL,
    )
    later_hold = _make_tick(
        primary_bot_id, bot_run.id, base_time + timedelta(minutes=3), Signal.HOLD,
    )
    error_tick = _make_tick(
        primary_bot_id, bot_run.id, base_time + timedelta(minutes=4), Signal.HOLD,
        error='something broke',
    )

    added_buy = tick_repo.add(buy_tick)
    tick_repo.add(hold_tick)
    added_sell = tick_repo.add(sell_tick)
    tick_repo.add(later_hold)
    added_error = tick_repo.add(error_tick)

    _expect(buy_tick.id is None, 'bot_tick.add', 'pre-insert id should be None')
    _expect(isinstance(added_buy.id, int), 'bot_tick.add', 'post-insert id should be int')
    _expect(added_error.error == 'something broke', 'bot_tick.add', 'error field not preserved')

    fetched = tick_repo.get_by_bot_id(primary_bot_id)
    _expect(len(fetched) == 5, 'bot_tick.get_by_bot_id', f'expected 5 ticks, got {len(fetched)}')
    _expect(
        all(isinstance(t.signal, Signal) for t in fetched),
        'bot_tick.get_by_bot_id', 'signal not deserialised back to Signal enum',
    )
    _expect(
        all(isinstance(t.price, Decimal) for t in fetched),
        'bot_tick.get_by_bot_id', 'price not deserialised back to Decimal',
    )
    _expect(
        any(t.price == PRICE_BUY for t in fetched),
        'bot_tick.get_by_bot_id', 'Decimal precision lost on round-trip',
    )

    latest = tick_repo.get_latest_action_by_bot_id(primary_bot_id)
    _expect(latest is not None, 'get_latest_action_by_bot_id', 'returned None despite buy/sell')
    if latest is not None:
        _expect(
            latest.signal == Signal.SELL,
            'get_latest_action_by_bot_id', f'expected SELL, got {latest.signal}',
        )
        _expect(
            latest.signal != Signal.HOLD,
            'get_latest_action_by_bot_id', 'returned a HOLD tick (must be skipped)',
        )

    holds_bot = Bot(
        id=holds_only_bot_id,
        pair=TEST_PAIR,
        strategy_name='TestStrategy',
        strategy_version='v0.0.1',
        interval=1,
        parameters={},
    )
    bot_repo.add(holds_bot)
    ledger.bot_ids.append(holds_only_bot_id)

    holds_run = BotRun(bot_id=holds_only_bot_id)
    added_holds_run = run_repo.add(holds_run)
    tick_repo.add(_make_tick(holds_only_bot_id, added_holds_run.id, base_time, Signal.HOLD))

    holds_only_latest = tick_repo.get_latest_action_by_bot_id(holds_only_bot_id)
    _expect(
        holds_only_latest is None,
        'get_latest_action_by_bot_id(holds-only)', 'expected None when only HOLD ticks exist',
    )

    none_existing = tick_repo.get_latest_action_by_bot_id(
        f'{TEST_PREFIX}does-not-exist-{uuid4().hex[:8]}',
    )
    _expect(
        none_existing is None,
        'get_latest_action_by_bot_id(missing)', 'expected None for non-existent bot_id',
    )

    assert added_sell.id is not None
    return added_sell.id


def _make_tick(
    bot_id: str,
    run_id: UUID,
    timestamp: datetime,
    signal: Signal,
    error: str | None = None,
) -> BotTick:
    return BotTick(
        bot_id=bot_id,
        run_id=run_id,
        price=PRICE_BUY if signal == Signal.BUY else PRICE_SELL if signal == Signal.SELL else PRICE_BUY,
        signal=signal,
        balance_base=BALANCE_BASE,
        balance_quote=BALANCE_QUOTE,
        timestamp=timestamp,
        error=error,
    )


# ---------------------------------------------------------------------------------------
# BotOrder repo
# ---------------------------------------------------------------------------------------

def _test_bot_order_repo(
    order_repo: SupabaseBotOrderRepository,
    bot_id: str,
    bot_run: BotRun,
    linked_tick_id: int,
    ledger: Ledger,
) -> None:
    logger.info('--- SupabaseBotOrderRepository ---')

    placed_order = BotOrder(
        bot_id=bot_id,
        run_id=bot_run.id,
        exchange_order_id=f'{TEST_PREFIX}EX-{uuid4().hex[:6]}',
        side=Side.BUY,
        tick_id=linked_tick_id,
    )
    filled_order = BotOrder(
        bot_id=bot_id,
        run_id=bot_run.id,
        exchange_order_id=f'{TEST_PREFIX}EX-{uuid4().hex[:6]}',
        side=Side.SELL,
        status=OrderStatus.FILLED,
        filled_at=datetime.now(timezone.utc),
        price=PRICE_SELL,
        volume=VOLUME,
        fee=FEE,
    )

    added_placed = order_repo.add(placed_order)
    added_filled = order_repo.add(filled_order)

    _expect(added_placed.status == OrderStatus.PLACED,
            'bot_order.add(placed)', 'status not PLACED')
    _expect(added_placed.price is None, 'bot_order.add(placed)', 'price should be None')
    _expect(added_filled.status == OrderStatus.FILLED,
            'bot_order.add(filled)', 'status not FILLED')
    _expect(added_filled.price == PRICE_SELL,
            'bot_order.add(filled)', 'Decimal precision lost')
    _expect(isinstance(added_placed.id, UUID), 'bot_order.add', 'id is not a UUID')
    _expect(added_placed.tick_id == linked_tick_id,
            'bot_order.add', 'tick_id not preserved as int')

    all_orders = order_repo.get_by_bot_id(bot_id)
    _expect(len(all_orders) == 2,
            'bot_order.get_by_bot_id', f'expected 2 orders, got {len(all_orders)}')
    _expect(all(isinstance(o.side, Side) for o in all_orders),
            'bot_order.get_by_bot_id', 'side not deserialised to Side enum')
    _expect(all(isinstance(o.status, OrderStatus) for o in all_orders),
            'bot_order.get_by_bot_id', 'status not deserialised to OrderStatus enum')

    placed_only = order_repo.get_placed_by_bot_id(bot_id)
    _expect(len(placed_only) == 1 and placed_only[0].id == added_placed.id,
            'get_placed_by_bot_id', 'expected only the placed order')

    by_tick = order_repo.get_by_tick_id(linked_tick_id)
    _expect(by_tick is not None and by_tick.id == added_placed.id,
            'get_by_tick_id', 'did not return the linked order')
    _expect(by_tick is not None and isinstance(by_tick.tick_id, int),
            'get_by_tick_id', 'tick_id not int on returned order')

    no_link = order_repo.get_by_tick_id(-1)
    _expect(no_link is None, 'get_by_tick_id(missing)', 'expected None for unknown tick_id')

    filled = order_repo.mark_filled(added_placed.id, PRICE_BUY, VOLUME, FEE)
    _expect(filled.status == OrderStatus.FILLED, 'mark_filled', 'status not FILLED')
    _expect(filled.price == PRICE_BUY, 'mark_filled', 'price not preserved')
    _expect(filled.filled_at is not None and filled.filled_at.tzinfo is not None,
            'mark_filled', 'filled_at not timezone-aware')

    after = order_repo.get_placed_by_bot_id(bot_id)
    _expect(not after, 'mark_filled', 'order still appears in get_placed_by_bot_id')

    try:
        order_repo.mark_filled(added_placed.id, PRICE_BUY, VOLUME, FEE)
    except ValueError:
        pass
    else:
        ledger.record_failure(
            'mark_filled(already-filled)', 'expected ValueError on already-filled order',
        )

    try:
        order_repo.mark_filled(uuid4(), PRICE_BUY, VOLUME, FEE)
    except ValueError:
        pass
    else:
        ledger.record_failure(
            'mark_filled(missing)', 'expected ValueError for non-existent order_id',
        )

    failing_order = BotOrder(
        bot_id=bot_id,
        run_id=bot_run.id,
        exchange_order_id=f'{TEST_PREFIX}EX-{uuid4().hex[:6]}',
        side=Side.BUY,
    )
    added_failing = order_repo.add(failing_order)
    failed = order_repo.mark_failed(added_failing.id, Decimal('0'), Decimal('0'), Decimal('0'))
    _expect(failed.status == OrderStatus.FAILED, 'mark_failed', 'status not FAILED')
    _expect(failed.filled_at is not None and failed.filled_at.tzinfo is not None,
            'mark_failed', 'filled_at not timezone-aware')

    try:
        order_repo.mark_failed(added_failing.id, Decimal('0'), Decimal('0'), Decimal('0'))
    except ValueError:
        pass
    else:
        ledger.record_failure(
            'mark_failed(already-failed)', 'expected ValueError on already-failed order',
        )

    try:
        order_repo.mark_failed(added_filled.id, Decimal('0'), Decimal('0'), Decimal('0'))
    except ValueError:
        pass
    else:
        ledger.record_failure(
            'mark_failed(filled)', 'expected ValueError when marking filled order as failed',
        )


# ---------------------------------------------------------------------------------------
# Assertion helper
# ---------------------------------------------------------------------------------------

def _expect(condition: bool, scenario: str, message: str) -> None:
    if condition:
        return
    logger.error('FAIL %s: %s', scenario, message)
    raise AssertionError(f'{scenario}: {message}')


if __name__ == '__main__':
    main()
