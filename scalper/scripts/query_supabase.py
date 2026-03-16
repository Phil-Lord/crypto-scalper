import json
import logging
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import questionary

from data_system import (
    Bot, BotOrder, BotRun, BotTick, OrderStatus, Side, Signal, SupabaseBotOrderRepository, SupabaseBotRepository,
    SupabaseBotRunRepository, SupabaseBotTickRepository, SupabaseClient
)
from utils import load_env, LOG_FORMAT

load_env()
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def query_supabase():
    table = questionary.select(
        'Table:', choices=['bots', 'bot_runs', 'bot_ticks', 'bot_orders']).ask()
    client = SupabaseClient()

    if table == 'bots':
        action = questionary.select('Action:', choices=['add', 'get']).ask()
        bot(action, client)
    elif table == 'bot_runs':
        action = questionary.select('Action:', choices=['add', 'get']).ask()
        bot_run(action, client)
    elif table == 'bot_ticks':
        action = questionary.select('Action:', choices=['add', 'get', 'get_latest_action']).ask()
        bot_tick(action, client)
    elif table == 'bot_orders':
        action = questionary.select('Action:', choices=['add', 'get', 'get_placed', 'update']).ask()
        bot_order(action, client)


def bot(action: str, client: SupabaseClient):
    repository = SupabaseBotRepository(client)
    if action == 'add':
        bot = repository.add(Bot(
            id=ask('id:', required=True),
            pair=ask('pair:', required=True),
            strategy_name=ask('strategy_name:', required=True),
            strategy_version=ask('strategy_version:', required=True),
            interval=int(ask('interval:', required=True)),
            parameters=json.loads(ask('parameters:', required=True))
        ))
        print('Added bot:', bot)
    elif action == 'get':
        bot = repository.get(ask('bot_id:', required=True))
        print('Retrieved bot:', bot)


def bot_run(action: str, client: SupabaseClient):
    repository = SupabaseBotRunRepository(client)
    if action == 'add':
        bot_run = repository.add(BotRun(
            bot_id=ask('bot_id:', required=True)
        ))
        print('Added bot run:', bot_run)
    elif action == 'get':
        bot_run = repository.get(UUID(ask('bot_run_id:', required=True)))
        print('Retrieved bot run:', bot_run)


def bot_tick(action: str, client: SupabaseClient):
    repository = SupabaseBotTickRepository(client)
    if action == 'add':
        bot_tick = repository.add(BotTick(
            bot_id=ask('bot_id:', required=True),
            run_id=UUID(ask('run_id:', required=True)),
            timestamp=datetime.now(timezone.utc),
            price=Decimal(ask('price:', required=True)),
            signal=Signal(questionary.select('signal:', choices=['buy', 'hold', 'sell']).ask()),
            balance_base=Decimal(ask('balance_base:', required=True)),
            balance_quote=Decimal(ask('balance_quote:', required=True)),
            error=ask('error (optional):')
        ))
        print('Added bot tick:', bot_tick)
    elif action == 'get':
        bot_tick = repository.get_by_bot_id(ask('bot_id:', required=True))
        print('Retrieved bot ticks:', bot_tick)
    elif action == 'get_latest_action':
        bot_tick = repository.get_latest_action_by_bot_id(ask('bot_id:', required=True))
        print('Retrieved latest directional bot tick:', bot_tick)


def bot_order(action: str, client: SupabaseClient):
    repository = SupabaseBotOrderRepository(client)
    if action == 'add':
        bot_order = repository.add(BotOrder(
            bot_id=ask('bot_id:', required=True),
            run_id=UUID(ask('run_id:', required=True)),
            tick_id=int(v) if (v := ask('tick_id (optional):')) else None,
            exchange_order_id=ask('exchange_order_id:', required=True),
            side=Side(questionary.select('side:', choices=['buy', 'sell']).ask()),
            status=OrderStatus(questionary.select(
                'status:', choices=['placed', 'filled', 'failed']).ask()),
            filled_at=datetime.strptime(v, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc) if (
                v := ask('filled_at (optional, YYYY-MM-DD HH:MM:SS):')) else None,
            price=Decimal(v) if (v := ask('price (optional):')) else None,
            volume=Decimal(v) if (v := ask('volume (optional):')) else None,
            fee=Decimal(v) if (v := ask('fee (optional):')) else None,
        ))
        print('Added bot order:', bot_order)
    elif action == 'get':
        bot_order = repository.get_by_bot_id(ask('bot_id:', required=True))
        print('Retrieved bot orders:', bot_order)
    elif action == 'get_placed':
        placed_orders = repository.get_placed_by_bot_id(ask('bot_id:', required=True))
        print('Retrieved placed bot orders:', placed_orders)
    elif action == 'update':
        existing_orders = repository.get_by_bot_id(ask('bot_id:', required=True))
        if not existing_orders:
            print('No orders found for that bot ID.')
            return
        choices = {
            f'{order.exchange_order_id} | {order.status.value} | {order.placed_at}': order
            for order in existing_orders
        }
        selected_label = questionary.select('Select order:', choices=list(choices.keys())).ask()
        order = choices[selected_label]
        status_value = questionary.select('status:', choices=['placed', 'filled', 'failed']).ask()
        updated = replace(
            order,
            status=OrderStatus(status_value),
            filled_at=datetime.strptime(v, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc) if (
                v := ask('filled_at (optional, YYYY-MM-DD HH:MM:SS):')) else order.filled_at,
            price=Decimal(v) if (v := ask('price (optional):')) else order.price,
            volume=Decimal(v) if (v := ask('volume (optional):')) else order.volume,
            fee=Decimal(v) if (v := ask('fee (optional):')) else order.fee,
        )
        result = repository.update(updated)
        print('Updated bot order:', result)


def ask(message: str, required: bool = False) -> str | None:
    while True:
        answer = questionary.text(message).ask()
        if answer:
            return answer
        if not required:
            return None
        print('This field is required.')


if __name__ == '__main__':
    query_supabase()
