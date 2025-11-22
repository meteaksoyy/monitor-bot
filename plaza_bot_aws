import requests
import json
import smtplib
import os

API_URL = "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=en_GB&page=0&sort=+reactionData.aangepasteTotaleHuurprijs"
CACHE_FILE = "plaza_cache_aws.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_1 = os.environ["BOT_TO"]
TO_2 = os.environ["BOT_TO_2"]

def fetch_ids():
  try:
    data = requests.get(API_URL, timeout=15).json()
  except Exception as e:
    print("FETCH ERROR: ", e)
    return []
  if "data" not in data:
    print("UNEXPECTED JSON: ", data)
    return []
  listings = data["data"]

  # check only rental listings in Delft
  filtered = [
    item for item in listings
    if item.get("gemeenteGeoLocatieNaam") == "Delft"
    and item.get("rentBuy") == "Huur"
    and isinstance(item.get("totalRent"), (int, float))
    and item.get("totalRent") > 100
  ]
  return filtered

def notify(msg):
  recipients = [TO_1, TO_2]
  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(EMAIL, PASSWORD)
  server.sendmail(EMAIL, recipients, msg)

try:
  old_ids = json.load(open(CACHE_FILE))
except:
  old_ids = []

new_items = fetch_ids()
new_ids = [item["id"] for item in new_items]
added = [item for item in new_items if item["id"] not in old_ids]
if added:
  lines = []
  for item in added:
    address = f"{item.get('street', '')} {item.get('houseNumber', '')} {item.get('houseNumberAddition', '')}".strip()
    lines.append(f"- {address} (ID: {item['id']})")
    msg = "New Plaza Listings in Delft:\n\n" + "\n".join(lines)
  notify(msg)

json.dump(new_ids, open(CACHE_FILE, "w"))
