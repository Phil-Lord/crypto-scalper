from trade_executor.config import load_config
from trade_executor.trade_executor import TradeExecutor


def lambda_handler(event, context):
    config = load_config()
    executor = TradeExecutor(
        pair=config["pair"],
        interval=config["interval"],
        strategy_name=config["strategy_name"],
        **config["strategy_params"]
    )
    executor.run_once()
    return {"status": "ok"}
