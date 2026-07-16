import os
import zipfile
import requests

url = "https://github.com/tcgdex/cards-database/archive/refs/heads/master.zip"

base = "/volume1/web/pokemon-tracker"
zip_file = os.path.join(base, "cards-database.zip")
extract_to = os.path.join(base, "cards-database")

print("Downloading repository...")

r = requests.get(url, stream=True)

with open(zip_file, "wb") as f:
    for chunk in r.iter_content(8192):
        if chunk:
            f.write(chunk)

print("Download complete.")

if os.path.exists(extract_to):
    import shutil
    shutil.rmtree(extract_to)

os.makedirs(extract_to, exist_ok=True)

print("Extracting...")

with zipfile.ZipFile(zip_file, "r") as z:
    z.extractall(extract_to)

print("Done!")