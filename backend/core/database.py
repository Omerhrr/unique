
from sqlmodel import create_engine, SQLModel, Session
import os

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("--- Database_url not found")
    DATABASE_URL = "sqlite:///../database.db"

engine = create_engine(DATABASE_URL, echo=True)
def create_db_and_tables():
    """
    Initializes the database by creating all tables defined by SQLModel.
    """
    print("Creating database and tables...")
    SQLModel.metadata.create_all(engine, checkfirst=True)

    print("Database and tables created successfully.")

def get_session():
    """
    A FastAPI dependency to provide a database session to endpoints.
    """
    with Session(engine) as session:
        yield session


