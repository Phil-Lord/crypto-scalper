import os
from pathlib import Path

from dotenv import load_dotenv


def get_env_var(env_var_name: str) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(dotenv_path=repo_root / '.env', override=False)
    return os.getenv(env_var_name)
