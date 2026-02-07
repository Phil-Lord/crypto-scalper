from pathlib import Path

# Local directories
ROOT_DIR = Path(__file__).resolve().parents[2]  # /path/to/repos/crypto-scalper

# External database URLs
OPTUNA_DB_URL = 'postgresql://optuna_user:password@localhost:5432/optuna_db'

# Logging
LOG_FORMAT = '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
