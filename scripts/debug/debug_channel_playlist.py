import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# When running inside container, /app is the root, so src is available directly
# But just in case, let's add current directory
sys.path.append(os.getcwd())

from src.database import Base
from src.models.schedule import Playlist, ScheduleSlot
from src.models.telegram import Channel

# Use env var or default
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sattva_streamer")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_channel_status(channel_id_str):
    db = SessionLocal()
    try:
        print(f"Checking channel: {channel_id_str}")
        channel = db.query(Channel).filter(text(f"id = '{channel_id_str}'")).first()
        if not channel:
            print("Channel not found!")
            return

        print(f"Channel Name: {channel.name}")
        
        # Check active slots
        print("\n--- Active Schedule Slots ---")
        slots = db.query(ScheduleSlot).filter(
            text(f"channel_id = '{channel_id_str}'"),
            ScheduleSlot.is_active == True
        ).all()
        for slot in slots:
            print(f"Slot: {slot.start_time}-{slot.end_time}, Playlist: {slot.playlist_id}")

        # Check assigned playlists
        print("\n--- Assigned Playlists (Ordered by Created At DESC) ---")
        playlists = db.query(Playlist).filter(
            text(f"channel_id = '{channel_id_str}'")
        ).order_by(Playlist.created_at.desc()).all()
        
        if not playlists:
            print("No playlists found for this channel.")
        
        for p in playlists:
            print(f"Playlist: {p.name} (ID: {p.id})")
            print(f"  Created At: {p.created_at}")
            print(f"  Active: {p.is_active}")
            print(f"  Items count: {len(p.items) if p.items else 0}")
            
    finally:
        db.close()

if __name__ == "__main__":
    check_channel_status("75b8dcc5-efac-45f7-8395-7961f204c2e6")
