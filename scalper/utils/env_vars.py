import os

from dotenv import load_dotenv

from .constants import ROOT_DIR


def load_env() -> None:
    '''
    Load environment variables from .env file.

    Call this once at application entry points (scripts, main.py).
    In production (AWS), this is a no-op since env vars come from the platform.
    '''
    load_dotenv(dotenv_path=ROOT_DIR / '.env', override=False)
