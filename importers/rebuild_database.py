import subprocess
import sys

steps = [
    "import_series.py",
    "import_sets.py",
    "import_cards.py",
    "import_images.py",
]

print("=" * 60)
print(" EvoDeck Database Rebuild")
print("=" * 60)

for step in steps:

    print()
    print(f"Running {step}")

    result = subprocess.run(
        [sys.executable, step]
    )

    if result.returncode != 0:
        print()
        print(f"{step} FAILED")
        break

print()
print("=" * 60)
print("Finished")
print("=" * 60)