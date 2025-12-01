from pathlib import Path

# Local directories
ROOT_DIR = Path(__file__).resolve().parents[2]  # /path/to/repos/crypto-scalper
LOCAL_STORAGE_PATH = ROOT_DIR / 'scalper' / 'local_storage'
GEN_EVAL_DB_PATH = LOCAL_STORAGE_PATH / 'gen-eval.db'

# External database URLs
OPTUNA_DB_URL = 'postgresql://optuna_user:password@localhost:5432/optuna_db'
