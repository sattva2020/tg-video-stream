import sys
import os
import uvicorn

print("Starting debug_run.py")
print(f"CWD: {os.getcwd()}")

# Add src to sys.path
src_path = os.path.join(os.getcwd(), "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)
    print(f"Added {src_path} to sys.path")

try:
    from src.main import app
    print("Successfully imported app from src.main")
except ImportError as e:
    print(f"Failed to import app: {e}")
    # Try importing api to see if that's the issue
    try:
        import api
        print("Successfully imported api")
    except ImportError as e2:
        print(f"Failed to import api: {e2}")
    sys.exit(1)

if __name__ == "__main__":
    print("Starting Uvicorn...")
    # Run without reload to avoid subprocess issues
    uvicorn.run(app, host="0.0.0.0", port=8080)
