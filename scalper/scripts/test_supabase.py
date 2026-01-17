from datetime import datetime
import questionary

from data_system import Bot, BotRun, BotTick, SupabaseBotRepository, SupabaseBotRunRepository, SupabaseBotTickRepository


def test_supabase():
    table = questionary.select('Select a table:', choices=['bots', 'bot_runs', 'bot_ticks']).ask()
    action = questionary.select('Select an action:', choices=['add', 'get']).ask()

    if table == 'bots':
        bot(action)
    elif table == 'bot_runs':
        bot_run(action)
    elif table == 'bot_ticks':
        bot_tick(action)


def bot(action: str):
    repository = SupabaseBotRepository()
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


def bot_run(action: str):
    repository = SupabaseBotRunRepository()
    if action == 'add':
        bot_run = repository.add(BotRun(
            bot_id=ask('bot_id:'),
            started_at=ask_datetime('started_at:'),
        ))
        print('Added bot run:', bot_run)
    elif action == 'get':
        bot_run = repository.get(ask('bot_run_id:'))
        print('Retrieved bot run:', bot_run)


def bot_tick(action: str):
    repository = SupabaseBotTickRepository()
    if action == 'add':
        bot_tick = repository.add(BotTick(
            bot_id=ask('bot_id:'),
            run_id=ask('bot_run_id:'),
            timestamp=ask_datetime('timestamp:'),
            balance_base=ask('balance_base:'),
            balance_quote=ask('balance_quote:'),
            price=ask('price:'),
            signal=ask('signal:'),
            order_executed=questionary.confirm('order_executed:').ask(),
            executed_at=ask_datetime('executed_at:'),
            execution_price=ask('execution_price:'),
            execution_volume=ask('execution_volume:'),
            execution_fee=ask('execution_fee:'),
            error=ask('error:')
        ))
        print('Added bot tick:', bot_tick)
    elif action == 'get':
        bot_tick = repository.get_by_bot_id(ask('bot_id:'))
        print('Retrieved bot ticks:', bot_tick)


def ask(message: str) -> str:
    return questionary.text(message).ask()


def ask_datetime(message: str) -> datetime:
    return datetime.strptime(ask(message), '%Y-%m-%d %H:%M:%S')


if __name__ == "__main__":
    test_supabase()
