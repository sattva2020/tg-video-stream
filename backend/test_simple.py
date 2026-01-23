import sys
from pathlib import Path

output_file = Path(__file__).parent / 'simple_test.txt'

try:
    with open(output_file, 'w') as f:
        f.write("Python script executed\n")
        f.write(f"Python version: {sys.version}\n")
        f.write(f"Working dir: {Path.cwd()}\n")
        f.write("SUCCESS\n")
except Exception as e:
    with open(output_file, 'w') as f:
        f.write(f"ERROR: {e}\n")
