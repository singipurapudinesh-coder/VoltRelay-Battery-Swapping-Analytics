from pathlib import Path
from src import config

# Get the swap events file path from config.py
path = config.SWAP_EVENTS_FILE

print("File path:", path)
print("File exists:", path.exists())

if path.exists():
    print("File size (GB):", round(path.stat().st_size / (1024**3), 3))

    print("\nFirst 5 lines / bytes of the file:")

    with open(path, "rb") as file:
        for i in range(5):
            line = file.readline()
            print(f"Line {i + 1}:", repr(line[:500]))
else:
    print("\nERROR: Swap events file was not found.")
    print("Check the file name and location inside data/raw/")