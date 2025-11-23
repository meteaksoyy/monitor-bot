import requests
import json
import smtplib
import os
from bs4 import BeautifulSoup

API_URL= "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=en_GB&page=0&sort=+reactionData.aangepasteTotaleHuurprijs"
CACHE_FILE = "plaza_cache_auto.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_1 = os.environ["BOT_TO"]
TO_2 = os.environ["BOT_TO_2"]

PLAZA_USERNAME = os.environ["PLAZA_USERNAME"]
PLAZA_PASSWORD = os.environ["PLAZA_PASSWORD"]

PLAZA_BASE = "https://plaza.newnewnew.space"
LOGIN_URL = "https://plaza.newnewnew.space/portal/proxy/frontend/api/v1/oauth/token"
APPLY_URL = "https://plaza.newnewnew.space/portal/object/frontend/react/format/json"
META_URL = "https://plaza.newnewnew.space/portal/object/frontend/getreageerconfiguration/format/json"

GENDER_ID = 0
INITIALS = "MA"
POSTCODE = "2613DD"
HUISNUMMER = "89"



# -----------------------------------------------------------------
# EMAIL NOTIFICATIONS
# -----------------------------------------------------------------
def notify(msg):
  email_text = f"Subject: Plaza Bot Alert\n\n{msg}"
  recipients = [TO_1, TO_2]
  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(EMAIL, PASSWORD)
  server.sendmail(EMAIL, recipients, email_text)
  server.quit()



# -----------------------------------------------------------------
# FETCH LISTINGS
# -----------------------------------------------------------------
def fetch_ids():
  try:
    data = requests.get(API_URL, timeout=10).json()
  except Exception as e:
    print("FETCH ERROR: ", e)
    return []
  if "data" not in data:
    print("UNEXPECTED JSON:", data)
    return []
  listings = data["data"]
  filtered = [
    item for item in listings
    if item.get("gemeenteGeoLocatieNaam") == "Delft"
    and item.get("rentBuy") == "Huur"
    and isinstance(item.get("totalRent"),(int, float))
    and item.get("totalRent") > 100
  ]
  return filtered

# ------------------------------------------------
# LOGIN
# ------------------------------------------------
def login(session: requests.Session):
  session.headers.update({
      "User-Agent": "Mozilla/5.0",
      "Accept": "application/json",
      "Content-Type": "application/json",
      "Origin": "https://plaza.newnewnew.space",
      "Referer": "https://plaza.newnewnew.space/",
  })
  payload = {
    "client_id": "wzp",
    "grant_type": "password",
    "username": PLAZA_USERNAME,
    "password": PLAZA_PASSWORD
  }
  r = session.post(LOGIN_URL, json=payload)
  if r.status_code != 200:
    raise Exception(f"Login failed: {r.status_code} {r.text}")
  return True

# ---------------------------------------------------
# GET HIDDEN FORM FIELDS
# ---------------------------------------------------
def fetch_metadata(session, dwelling_id):
  url = f"{META_URL}?dwellingID={dwelling_id}"
  r = session.get(url)
  if r.status_code != 200:
    raise Exception("Metadata fetch failed")

  data = r.json()

  if "reageerConfiguration" not in data:
    raise Exception("Invalid metadata: missing reageerConfiguration")
  config = data["reageerConfiguration"]
  elements = config.get("elements", {})
  
  hash_block = elements.get("__hash__", {})
  hash_value = hash_block.get("initialData", "")
  if not hash_value:
    raise Exception("Missing hash value in metadata")
  return hash_value
  
# ---------
# APPLY
# ---------
def apply_to_listing(session, body):
  r = session.post(APPLY_URL, json=body)
  if r.status_code != 200:
    raise Exception(f"Apply failed {r.status_code} {r.text}")
  return r.json()

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------

try:
  old_ids = json.load(open(CACHE_FILE))
except:
  old_ids = []

new_items = fetch_ids()
new_ids = [item["id"] for item in new_items]
added = [item for item in new_items if item["id"] not in old_ids]

if added:
  with requests.Session() as session:
    login(session)
  
    msg_lines = []
    for item in added:
      dwelling_id = str(item["id"])
      reaction_url = item.get("reactionData", {}).get("url", "")
      try:
        params = dict(pair.split("=") for pair in reaction_url.lstrip("?").split("&"))
        add_value = params.get("add")
        dynamic_dwelling = params.get("dwellingID")
      except Exception as e:
        add_value = None
        dynamic_dwelling = None
      if not add_value or not dynamic_dwelling:
        msg_lines.append(f"- ID {dwelling_id}: missing add/dwellingID")
        continue
      
      try:
        hash_val = fetch_metadata(session, dwelling_id)
      except Exception as e:
        msg_lines.append(f"- ID {dwelling_id}: metadata error: {e}")
        continue

      payload = {
        "__id__":"",
        "__hash__": hash_val,
        "genderID": GENDER_ID,
        "initials": INITIALS,
        "postcode": POSTCODE,
        "huisnummer": HUISNUMMER,
        "reactieMotivatie": "",
        "add": add_value,
        "dwellingID": dynamic_dwelling
      }

      try:
        result = apply_to_listing(session, payload)
        msg_lines.append(f"- {dwelling_id} applied successfully -> {result}")
      except Exception as e:
        msg_lines.append(f"- {dwelling_id} apply failed -> {e}")
    notify("\n".join(msg_lines))
# save cache
json.dump(new_ids, open(CACHE_FILE, "w"))
