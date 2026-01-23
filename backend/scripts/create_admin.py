import sys
import os
import argparse

# Add the src directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import SessionLocal
from models.user import User

def create_admin(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"User with email {email} not found.")
            return

        user.role = "admin"
        user.status = "approved"
        db.commit()
        print(f"User {email} is now an admin and approved.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to admin role.")
    parser.add_argument("email", help="The email of the user to promote")
    args = parser.parse_args()

    create_admin(args.email)
