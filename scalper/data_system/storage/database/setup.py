import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

# Get the store directory and a create path to the trading-pair-specific csv file.
DATABASE_DIR = os.path.join(os.path.dirname(__file__))
os.makedirs(DATABASE_DIR, exist_ok=True)
DATABASE_URL = f'sqlite:///{DATABASE_DIR}/trades.db'

# Create an engine and a factory for constructing session objects against it.
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine)


def initialise_database():
    '''
    Use table metadata and the engine to generate the database schema.
    '''
    Base.metadata.create_all(bind=engine)
