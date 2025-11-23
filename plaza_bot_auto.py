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
LOGIN_URL = f"{PLAZA_BASE}/portaal/account/frontend/loginservice/format/json"
APPLY_URL = f"{PLAZA_BASE}/portaal/object/frontend/react/format/json"


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
def fetch_form_fields(session: requests.Session, url: str):
  r = session.get(url)
  if r.status_code != 200:
    raise Exception(f"Detail page load failed: {r.status_code}")
  soup = BeautifulSoup(r.text, "html.parser")
  form = soup.find("form", attrs={"name": "reactForm"})
  if not form:
    raise Exception("Apply form not found - are you logged in?")
  fields = {}
  for inp in form.find_all("input"):
    name = inp.get("name")
    val = inp.get("value") or ""
    if name:
      fields[name] = val
  required = ["__id__", "__hash__", "add", "dwellingID"]
  for k in required:
    if k not in fields:
      raise Exception(f"Missing required form field: {k}")
  return fields

# ---------
# APPLY
# ---------
def apply_to_listing(session: requests.Session, fields:dict):
  r = session.post(APPLY_URL, data=fields)
  if r.status_code != 200:
    raise Exception(f"Apply failed {r.status_code} {r.text}")
  return r.json()

try:
  old_ids = json.load(open(CACHE_FILE))
except:
  old_ids = []

new_items = fetch_ids()
new_ids = [item["id"] for item in new_items]
added = [item for item in new_items if item["id"] not in old_ids]

if added:
  with requests.Session() as session:
    session.headers.update({"User-Agent": "Mozilla/5.0"})
    login(session)
    msg_lines = []
    for item in added:
      address = f"{item.get('street', '')} {item.get('houseNumber','')} {item.get('houseNumberAddition', '')}".strip()
      url_key = item.get("urlKey", "")
      detail_url = f"{PLAZA_BASE}/en/availables-places/living-place/details/{url_key}"
      try:
        fields = fetch_form_fields(session, detail_url)
        apply_result = apply_to_listing(session, fields)
        apply_msg = f"Applied successfully: {apply_result}"
      except Exception as e:
        apply_msg = f"Apply failed: {e}"
      msg_lines.append(f"- {address} (ID: {item['id']})\n {detail_url}\n {apply_msg}\n")
    final_msg = "New Plaza Listings in Delft:\n\n" + "\n".join(msg_lines)
    notify(final_msg)
# save cache
json.dump(new_ids, open(CACHE_FILE, "w"))
