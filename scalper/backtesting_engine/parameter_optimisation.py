import os
import sqlite3

import optuna

from strategy_manager import StrategyManager


def optimise_parameters(engine, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
    def objective(trial: optuna.Trial) -> float:
        params = {}
        for param_name, param_range in param_grid.items():
            params[param_name] = trial.suggest_int(param_name, param_range[0], param_range[1])

        strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
        engine.strategy = strategy
        engine.run()
        final_quote_balance = engine.get_final_quote_balance()

        print(f'{trial.number}: {final_quote_balance} {params}')
        return final_quote_balance

    db_dir = os.path.join(os.path.dirname(__file__))
    os.makedirs(db_dir, exist_ok=True)
    db_url = f'sqlite:///{db_dir}/optimisation_shared/optimisation.db'

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(
            n_startup_trials=10,
            multivariate=True,
            group=True,
            constant_liar=True
        ),
        storage=db_url,
        load_if_exists=True
    )

    # Enable Write-Ahead Logging (WAL) mode
    conn = sqlite3.connect(f'{db_dir}/optimisation_shared/optimisation.db')
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")  # Better performance than FULL
    conn.close()

    study.optimize(objective, n_trials=n_trials, n_jobs=-1)

    return {
        'best_params': study.best_params,
        'best_profit': study.best_value,
        'study': study
    }


def optimise_parameters_postgres(engine, param_grid: dict[str, list[any]], n_trials: int = 100) -> dict[str, any]:
    def objective(trial: optuna.Trial) -> float:
        params = {}
        for param_name, param_range in param_grid.items():
            params[param_name] = trial.suggest_int(param_name, param_range[0], param_range[1])

        strategy = StrategyManager().get_strategy(engine.strategy.__class__.__name__, **params)
        engine.strategy = strategy
        engine.run()
        final_quote_balance = engine.get_final_quote_balance()

        print(f'{trial.number}: {final_quote_balance} {params}')
        return final_quote_balance

    study_name = f'{engine.strategy.__class__.__name__}-{engine.pair}-{engine.start}-{engine.end}'
    db_url = ''
    storage = optuna.storages.RDBStorage(
        url=db_url,
        engine_kwargs={'pool_size': 10, 'max_overflow': 10, 'pool_pre_ping': True}
    )

    study = optuna.create_study(
        study_name=study_name,
        storage=storage,
        load_if_exists=True,
        direction='maximize',
        sampler=optuna.samplers.TPESampler(
            n_startup_trials=10,
            multivariate=True,
            group=True,
            constant_liar=True
        )
    )
    study.optimize(objective, n_trials=n_trials, n_jobs=-1)
