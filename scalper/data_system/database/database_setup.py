from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base
from utils import TRADES_DB_PATH

# Create an engine and a factory for constructing session objects against it.
engine = create_engine(f'sqlite:///{TRADES_DB_PATH}')
SessionLocal = sessionmaker(bind=engine)


def initialise_database():
    ''' Use table metadata and the engine to generate the database schema. '''
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialise_database()
