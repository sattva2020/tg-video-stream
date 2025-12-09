import sys
import os
from sqlalchemy import text
from src.database import SessionLocal
from src.models.schedule import ScheduleSlot

def check_slots():
    db = SessionLocal()
    try:
        print("Checking slots in DB...")
        # Query all slots
        slots = db.query(ScheduleSlot).order_by(ScheduleSlot.created_at.desc()).limit(10).all()
        
        if not slots:
            print("No slots found in database.")
            return

        print(f"Found {len(slots)} recent slots:")
        for slot in slots:
            print(f"ID: {slot.id}")
            print(f"  Channel ID: {slot.channel_id}")
            print(f"  Date: {slot.start_date}")
            print(f"  Time: {slot.start_time} - {slot.end_time}")
            print(f"  Repeat: {slot.repeat_type}")
            print(f"  Active: {slot.is_active}")
            print(f"  Created: {slot.created_at}")
            print("-" * 20)
            
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_slots()
