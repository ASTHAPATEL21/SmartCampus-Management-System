import bcrypt
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import User


# Ensure tables are created
Base.metadata.create_all(bind=engine)

def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def add_admin(email: str, password: str):
    """Add an admin user to the database."""
    db: Session = SessionLocal()

    # Hash the password
    hashed_password = hash_password(password)

    # Check if admin already exists
    existing_admin = db.query(User).filter(User.username == email).first()
    if existing_admin:
        print(f"Admin with email '{email}' already exists.")
        return

    # Create the admin user
    admin = User(username=email, hashed_password=hashed_password, role="admin")

    # Add to the database
    db.add(admin)
    db.commit()
    db.close()

    print(f"Admin user '{email}' added successfully!")

# Add the admin user
if __name__ == "__main__":
    add_admin(email="admin@example.com", password="admin@example.com")
