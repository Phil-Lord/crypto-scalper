import os


class _OptunaConfigMeta(type):
    @property
    def DB_URL(cls) -> str | None:
        return os.getenv('OPTUNA_DB_URL')


class OptunaConfig(metaclass=_OptunaConfigMeta):
    pass
