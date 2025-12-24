import sys
import os
import uuid
from datetime import datetime

import sys
import os
import uuid
from datetime import datetime

# Add both app and src to sys.path
app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.insert(0, app_path)
sys.path.insert(0, src_path)

from database import SessionLocal
from models.user import User
from api.auth.utils import get_password_hash

def create_user(email: str, password: str, role: str = "admin"):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if user:
            print(f"User with email {email} already exists.")
            return

        hashed_password = get_password_hash(password)
        user = User(
            id=uuid.uuid4(),
            email=email,
            hashed_password=hashed_password,
            role=role,
            status="approved",
            email_verified=True,
            created_at=datetime.utcnow()
        )
        db.add(user)
        db.commit()
        print(f"User {email} created successfully with role {role}.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create a new user.")
    parser.add_argument("email", help="The email of the user")
    parser.add_argument("password", help="The password of the user")
    parser.add_argument("--role", default="admin", help="The role of the user (default: admin)")
    args = parser.parse_args()

    create_user(args.email, args.password, args.role)
