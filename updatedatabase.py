from database import engine, Base
from models import User, Course, Grade, Assignment, Notification  # Import all your models


def recreate_database():
    # Drop all existing tables
    Base.metadata.drop_all(bind=engine)

    # Create all tables again
    Base.metadata.create_all(bind=engine)
    print("Database recreated successfully!")


if __name__ == "__main__":
    recreate_database()