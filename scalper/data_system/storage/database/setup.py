from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DATABASE_URL = 'sqlite:///trades.db'

# Create an engine and a factory for constructing session objects against it.
engine = create_engine(DATABASE_URL, echo=True)
LocalSession = sessionmaker(bind=engine)


def initialise_database():
    '''
    Use table metadata and the engine to generate the database schema.
    '''
    Base.metadata.create_all(bind=engine)
