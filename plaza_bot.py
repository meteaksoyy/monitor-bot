import requests
import json
import smtplib
import os

API_URL = "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=en_GB&page=0&sort=+reactionData.aangepasteTotaleHuurprijs"
CACHE_FILE = "plaza_cache.json"

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
  if "list" not in data:
    print("UNEXPECTED JSON: ", data)
    return []
  listings = data["data"]

  print("DEBUG SAMPLE: ", listings[:2])

  # check only rental listings in Delft
  filtered = [
    item for item in listings
    if item.get("gemeenteGeoLocatieNaam") == "Delft"
    and item.get("rentBuy") == "Huur"
  ]
  return [item["id"] for item in filtered]

def notify(msg):
  recipients = [TO_1, TO_2]
  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(EMAIL, PASSWORD)
  server.sendemail(EMAIL, recipients, msg)

try:
  old_ids = json.load(open(CACHE_FILE))
except:
  old_ids = []

new_ids = fetch_ids()
added = [i for i in new_ids if i not in old_ids]
if added:
  notify(f"NEW PLAZA LISTINGS IN DELFT:\n{added}")

json.dump(new_ids, open(CACHE_FILE, "w"))
  
