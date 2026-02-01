from datetime import datetime

import questionary

from data_system import (
    Bot, BotOrder, BotRun, BotTick, SupabaseBotOrderRepository, SupabaseBotRepository,
    SupabaseBotRunRepository, SupabaseBotTickRepository, SupabaseClient
)


def query_supabase():
    table = questionary.select(
        'Table:', choices=['bots', 'bot_runs', 'bot_ticks', 'bot_orders']).ask()
    action = questionary.select('Action:', choices=['add', 'get']).ask()

    client = SupabaseClient()
    if table == 'bots':
        bot(action, client)
    elif table == 'bot_runs':
        bot_run(action, client)
    elif table == 'bot_ticks':
        bot_tick(action, client)
    elif table == 'bot_orders':
        bot_order(action, client)


def bot(action: str, client: SupabaseClient):
    repository = SupabaseBotRepository(client)
    if action == 'add':
        bot = repository.add(Bot(
            id=ask('id:'),
            pair=ask('pair:'),
            strategy_name=ask('strategy_name:'),
            strategy_version=ask('strategy_version:'),
            interval=ask('interval:'),
            parameters=ask('parameters:')
        ))
        print('Added bot:', bot)
    elif action == 'get':
        bot = repository.get(ask('bot_id:'))
        print('Retrieved bot:', bot)


def bot_run(action: str, client: SupabaseClient):
    repository = SupabaseBotRunRepository(client)
    if action == 'add':
        bot_run = repository.add(BotRun(
            bot_id=ask('bot_id:'),
            started_at=ask_datetime('started_at:'),
        ))
        print('Added bot run:', bot_run)
    elif action == 'get':
        bot_run = repository.get(ask('bot_run_id:'))
        print('Retrieved bot run:', bot_run)


def bot_tick(action: str, client: SupabaseClient):
    repository = SupabaseBotTickRepository(client)
    if action == 'add':
        bot_tick = repository.add(BotTick(
            bot_id=ask('bot_id:'),
            run_id=ask('bot_run_id:'),
            timestamp=ask_datetime('timestamp:'),
            price=ask('price:'),
            signal=ask('signal:'),
            error=ask('error:'),
            balance_base=ask('balance_base:'),
            balance_quote=ask('balance_quote:')
        ))
        print('Added bot tick:', bot_tick)
    elif action == 'get':
        bot_tick = repository.get_by_bot_id(ask('bot_id:'))
        print('Retrieved bot ticks:', bot_tick)


def bot_order(action: str, client: SupabaseClient):
    repository = SupabaseBotOrderRepository(client)
    if action == 'add':
        bot_order = repository.add(BotOrder(
            bot_id=ask('bot_id:'),
            run_id=ask('bot_run_id:'),
            tick_id=ask('tick_id:'),
            side=ask('side:'),
            price=ask('price:'),
            volume=ask('volume:'),
            fee=ask('fee:'),
            executed_at=ask_datetime('executed_at:')
        ))
        print('Added bot order:', bot_order)
    elif action == 'get':
        bot_order = repository.get_by_bot_id(ask('bot_id:'))
        print('Retrieved bot orders:', bot_order)


def ask(message: str) -> str:
    return questionary.text(message).ask()


def ask_datetime(message: str) -> datetime:
    return datetime.strptime(ask(message), '%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    query_supabase()
