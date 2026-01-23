import sys
sys.path.insert(0, '.')
try:
    with open('test_log.txt', 'w') as f:
        f.write("Python script started\n")
        f.write(f"Python version: {sys.version}\n")
        import os
        f.write(f"Working directory: {os.getcwd()}\n")
        f.write(f".env exists: {os.path.exists('.env')}\n")
    print("SUCCESS")
except Exception as e:
    with open('test_log.txt', 'w') as f:
        f.write(f"ERROR: {e}\n")
    print("ERROR")
