#!/usr/bin/env python3
"""
Простой запуск backend без reload для отладки.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from src.main import app
    
    print("=" * 60)
    print("Starting Telegram Broadcast Backend")
    print("=" * 60)
    print(f"Host: 0.0.0.0")
    print(f"Port: 8000")
    print(f"Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
    except Exception as e:
        print(f"Error starting server: {e}")
        raise
