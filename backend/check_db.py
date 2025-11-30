import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", [t[0] for t in tables])

cursor.execute("PRAGMA table_info(users);")
print("\nUsers columns:", [c[1] for c in cursor.fetchall()])

cursor.execute("PRAGMA table_info(telegram_accounts);")
print("\nTelegramAccounts columns:", [c[1] for c in cursor.fetchall()])

cursor.execute("PRAGMA table_info(channels);")
print("\nChannels columns:", [c[1] for c in cursor.fetchall()])

cursor.execute("PRAGMA table_info(playlist_items);")
print("\nPlaylistItems columns:", [c[1] for c in cursor.fetchall()])

conn.close()
