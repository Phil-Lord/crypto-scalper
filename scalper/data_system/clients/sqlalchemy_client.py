from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data_system.config import LocalSQLiteConfig


class SQLAlchemyClient():
    ''' Creates SQLAlchemy engine and session for local SQLite DB '''

    def __init__(self, url: str | None = None) -> None:
        self.engine = create_engine(url or LocalSQLiteConfig.SCALPER_DB_URL)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)

    def connect(self) -> sessionmaker:
        return self.SessionLocal()

    def close(self) -> None:
        self.engine.dispose()
