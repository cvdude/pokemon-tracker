import requests

url = "https://api.github.com/repos/tcgdex/cards-database/contents/data/XY/Ancient%20Origins"

r = requests.get(url)

print("Status:", r.status_code)

files = r.json()

count = 0

for item in files:
    if item["name"].endswith(".ts"):
        count += 1
        print(item["name"])

print()
print("Total TS files:", count)