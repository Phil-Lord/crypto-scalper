import optuna

from strategy_manager import StrategyManager


def optimise_parameters(engine, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
    def objective(trial):
        params = {}
        for param_name, param_range in param_grid.items():
            if isinstance(param_range[0], int):
                params[param_name] = trial.suggest_int(param_name, param_range[0], param_range[1])
            elif isinstance(param_range[0], float):
                params[param_name] = trial.suggest_float(param_name, param_range[0], param_range[1])
            else:
                raise ValueError(f'Unsupported parameter type for {param_name}')

        strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
        engine.strategy = strategy

        results = engine.run()
        return engine.get_final_quote_balance()

    study = optuna.create_study(direction='maximize')
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    return {
        'best_params': study.best_params,
        'best_profit': study.best_value,
        'study': study
    }
