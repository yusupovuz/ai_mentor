from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:12345@localhost/ai_chat_db")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
session_local = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()
