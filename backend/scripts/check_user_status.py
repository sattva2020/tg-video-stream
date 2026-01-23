import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
from database import SessionLocal
from models.user import User

def check_user(email):
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    if user:
        print(f"User: {user.email}, Status: {user.status}, Role: {user.role}")
    else:
        print("User not found")
    db.close()

if __name__ == "__main__":
    check_user("admin@test.com")
