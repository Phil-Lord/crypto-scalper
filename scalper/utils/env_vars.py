import os

from dotenv import load_dotenv

from .constants import ROOT_DIR


def get_env_var(env_var_name: str) -> str:
    load_dotenv(dotenv_path=ROOT_DIR / '.env', override=False)
    return os.getenv(env_var_name)
