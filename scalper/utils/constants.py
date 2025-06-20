from pathlib import Path


OPTUNA_DB_URL = 'postgresql://optuna_user:password@localhost:5432/optuna_db'
ROOT_DIR = Path(__file__).resolve().parents[2]
