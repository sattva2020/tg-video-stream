import sys
import os
import uvicorn

if __name__ == "__main__":
    # Add src to sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=False)
