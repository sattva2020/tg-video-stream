import sys
import os
import argparse

# Add the src directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from database import SessionLocal
from models.user import User

def promote_user(email=None, telegram_username=None, telegram_id=None, role="admin"):
    db = SessionLocal()
    try:
        query = db.query(User)
        if email:
            query = query.filter(User.email == email)
        elif telegram_username:
            # Handle @ prefix if present
            if telegram_username.startswith('@'):
                telegram_username = telegram_username[1:]
            query = query.filter(User.telegram_username == telegram_username)
        elif telegram_id:
            query = query.filter(User.telegram_id == telegram_id)
        else:
            print("Error: Must provide email, telegram_username, or telegram_id")
            return

        user = query.first()
        if not user:
            print("User not found.")
            return

        user.role = role
        user.status = "approved"
        db.commit()
        print(f"User {user.id} (Email: {user.email}, TG: {user.telegram_username}) is now {role} and approved.")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Promote a user to a specific role.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--email", help="The email of the user")
    group.add_argument("--telegram-username", help="The Telegram username of the user")
    group.add_argument("--telegram-id", type=int, help="The Telegram ID of the user")
    
    parser.add_argument("--role", default="admin", choices=["admin", "superadmin", "operator", "moderator"], help="Role to assign")

    args = parser.parse_args()

    promote_user(email=args.email, telegram_username=args.telegram_username, telegram_id=args.telegram_id, role=args.role)
