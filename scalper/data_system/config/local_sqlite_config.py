from utils import ROOT_DIR


class LocalSQLiteConfig:
    LOCAL_STORAGE_PATH = ROOT_DIR / 'scalper' / 'local_storage'
    SCALPER_DB_URL = f'sqlite:///{LOCAL_STORAGE_PATH / 'scalper.db'}'
