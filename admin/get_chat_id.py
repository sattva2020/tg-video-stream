from pyrogram import Client
from dotenv import load_dotenv
import os
import sys
import traceback
import struct

load_dotenv()  # Загружает API_ID, API_HASH, SESSION_STRING из .env

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
SESSION = os.getenv("SESSION_STRING")

if not (API_ID and API_HASH and SESSION):
    print("ERROR: .env must contain API_ID, API_HASH and SESSION_STRING.\nPlease generate a session string first.")
    sys.exit(1)

# Decide whether SESSION is a path to a session file or an exported session string.
use_session_file = False
session_path = None

# Heuristics: if the value looks like a path and exists on disk, treat as session file.
if os.path.exists(SESSION):
    use_session_file = True
    session_path = SESSION
else:
    # If it looks like a file name (contains a path separator or endswith .session), consider it a path
    if any(sep in SESSION for sep in ("/", "\\")) or SESSION.lower().endswith('.session'):
        print("Note: SESSION_STRING looks like a path but file was not found.\nPlease verify the path or provide an exported session string.")

client_kwargs = {
    'api_id': int(API_ID),
    'api_hash': API_HASH,
}

if use_session_file:
    client_kwargs['session_name'] = session_path
else:
    # session_string is the recommended exported format; pass it directly
    client_kwargs['session_string'] = SESSION

app = Client("my_account", **client_kwargs)

def format_chat(chat):
    # Return a friendly title (fallback to username or id)
    title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or getattr(chat, 'username', None)
    if not title:
        title = f"<no-title-{chat.id}>"
    return title

def run():
    try:
        with app:
            # Iterate over all dialogs (uses internal pagination)
            print("Fetching dialogs... this may take a few seconds")
            for dialog in app.get_dialogs(limit=None):
                chat = dialog.chat
                title = format_chat(chat)
                # chat.type can be 'private', 'group', 'supergroup', 'channel'
                ctype = getattr(chat, 'type', 'unknown')
                print(f"{title}\t{ctype}\t{chat.id}")
    except Exception as exc:
        print("ERROR: failed to start Pyrogram client or fetch dialogs.")
        print("Exception type:", type(exc).__name__)
        # For struct.unpack errors (session corruption / wrong format) provide targeted guidance
        if isinstance(exc, struct.error):
            print("Likely cause: the provided SESSION_STRING is invalid or a corrupted session file.")
        else:
            # inspect common errors
            tb = traceback.format_exc()
            print(tb)

        print("Possible actions:")
        print(" - If you supplied a path to a .session file, ensure the file exists and is readable.")
        print(" - If you supplied an exported session string, make sure it is complete and wasn't truncated when copying into .env.")
        print(" - To regenerate safely: run `python generate_session_and_list_dialogs.py` (uses Pyrogram) or `python generate_session_telethon.py` (Telethon, can force SMS).")
        print(" - If in doubt, re-export the session on the machine where you ran the original session generation.")
        sys.exit(1)

if __name__ == '__main__':
    run()
