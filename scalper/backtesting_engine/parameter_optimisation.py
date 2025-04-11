import optuna

from strategy_manager import StrategyManager


def optimise_parameters(engine, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
    def objective(trial):
        params = {}
        for param_name, param_range in param_grid.items():
            params[param_name] = trial.suggest_int(param_name, param_range[0], param_range[1])

        strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
        engine.strategy = strategy
        engine.run()
        final_quote_balance = engine.get_final_quote_balance()

        print(f'{trial.number}: {final_quote_balance} {params}')
        return final_quote_balance

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(n_startup_trials=10, multivariate=True)
    )
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    return {
        'best_params': study.best_params,
        'best_profit': study.best_value,
        'study': study
    }
