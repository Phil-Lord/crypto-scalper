from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from data_system.config import LocalSQLiteConfig


class SQLAlchemyClient():
    ''' Creates SQLAlchemy engine and session for local SQLite DB '''

    def __init__(self, url: str | None = None) -> None:
        self.engine = create_engine(url or LocalSQLiteConfig.SCALPER_DB_URL)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False)

    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        '''
        Context manager for database sessions.

        Automatically commits on success, rolls back on error, and closes the session.

        Usage:
            with client.session() as session:
                session.execute(...)
        '''
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
