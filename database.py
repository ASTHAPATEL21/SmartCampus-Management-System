from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://smartcampus_user:smartcampus@localhost/smartcampus_db"

# Create the database engine
engine = create_engine(DATABASE_URL)

# Create a session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()
