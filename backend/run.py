import sys
import os
import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()
    
    # Add src to sys.path
    sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
    uvicorn.run("src.main:app", host=args.host, port=args.port, reload=False)
