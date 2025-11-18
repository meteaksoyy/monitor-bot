import requests
import json
import smtplib
import os
from bs4 import BeautifulSoup

API_URL = "https://www.verra.nl/en/realtime-listings/consumer"
CACHE_FILE = "cache.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_EMAIL = os.environ["BOT_TO"]

def fetch_ids():
    try:
        data = requests.get(API_URL, timeout=10).json()
    except Exception as e:
        print("ERROR FETCHING JSON:", e)
        return []

    print("DEBUG JSON SAMPLE:", data[:2])   # print first items
    return [item["id"] for item in data]

def notify(msg):
  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(EMAIL, PASSWORD)
  server.sendmail(EMAIL, TO_EMAIL, msg)

try:
  old_ids = json.load(open(CACHE_FILE))

except:
  old_ids = []

new_ids = fetch_ids()
added = [i for i in new_ids if i not in old_ids]

if added:
  notify(f"NEW LISTING APPLY RIGHT NOW :) : {added}")
  json.dump(new_ids, open(CACHE_FILE, "w"))

notify("TEST EMAIL FROM BOT")
