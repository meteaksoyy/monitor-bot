import requests
import json
import smtplib
import os

API_URL = (
    "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod"
    "?limit=60&locale=en_GB&page=0&sort=+reactionData.aangepasteTotaleHuurprijs"
)

CACHE_FILE = "plaza_cache_auto.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_1 = os.environ["BOT_TO"]
TO_2 = os.environ["BOT_TO_2"]

PLAZA_USERNAME = os.environ["PLAZA_USERNAME"]
PLAZA_PASSWORD = os.environ["PLAZA_PASSWORD"]

PLAZA_BASE = "https://plaza.newnewnew.space"
LOGIN_URL = f"{PLAZA_BASE}/portal/proxy/frontend/api/v1/oauth/token"
REACT_URL = f"{PLAZA_BASE}/portal/object/frontend/react/format/json"


# -------------------------------------------------------------
# EMAIL NOTIFICATIONS
# -------------------------------------------------------------
def notify(msg):
    body = f"Subject: Plaza Bot Alert\n\n{msg}"
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(EMAIL, PASSWORD)
    server.sendmail(EMAIL, [TO_1, TO_2], body)
    server.quit()


# -------------------------------------------------------------
# FETCH LISTINGS
# -------------------------------------------------------------
def fetch_ids():
    try:
        data = requests.get(API_URL, timeout=10).json()
    except Exception:
        return []

    if "data" not in data:
        return []

    return [
        item for item in data["data"]
        if item.get("gemeenteGeoLocatieNaam") == "Delft"
        and item.get("rentBuy") == "Huur"
        and isinstance(item.get("totalRent"), (int, float))
        and item.get("totalRent") > 100
    ]


# -------------------------------------------------------------
# LOGIN
# -------------------------------------------------------------
def login(session):
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": PLAZA_BASE,
        "Referer": PLAZA_BASE + "/",
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


# -------------------------------------------------------------
# FETCH HASH FOR SPECIFIC LISTING
# -------------------------------------------------------------
def fetch_hash(session, add_value, dwelling_id):
    url = f"{REACT_URL}?add={add_value}&dwellingID={dwelling_id}"

    r = session.get(url)
    if r.status_code != 200:
        raise Exception("Failed to fetch react metadata")

    data = r.json()

    elements = data.get("elements", {})
    hash_obj = elements.get("__hash__", {})
    hash_val = hash_obj.get("initialData")

    if not hash_val:
        raise Exception("Missing __hash__ in metadata")

    return hash_val


# -------------------------------------------------------------
# APPLY
# -------------------------------------------------------------
def apply_to_listing(session, payload):
    r = session.post(REACT_URL, json=payload)
    if r.status_code != 200:
        raise Exception(f"Apply failed {r.status_code} {r.text}")
    return r.json()


# -------------------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------------------
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

        messages = []

        for item in added:
            listing_id = str(item["id"])

            # Extract add & dwellingID from reactionData.url
            reaction_url = item.get("reactionData", {}).get("url")
            if not reaction_url:
                messages.append(f"- ID {listing_id}: missing reactionData.url")
                continue

            params = dict(pair.split("=") for pair in reaction_url.lstrip("?").split("&"))
            add_value = params.get("add")
            dwelling_value = params.get("dwellingID")

            if not add_value or not dwelling_value:
                messages.append(f"- ID {listing_id}: invalid reactionData.url")
                continue

            # Fetch __hash__
            try:
                hash_val = fetch_hash(session, add_value, dwelling_value)
            except Exception as e:
                messages.append(f"- ID {listing_id}: hash fetch failed → {e}")
                continue

            # Build final payload
            payload = {
                "__id__": "Portal_Form_SubmitOnly",
                "__hash__": hash_val,
                "add": add_value,
                "dwellingID": dwelling_value
            }

            # Apply
            try:
                result = apply_to_listing(session, payload)
                messages.append(f"- ID {listing_id}: applied successfully → {result}")
            except Exception as e:
                messages.append(f"- ID {listing_id}: apply failed → {e}")

        notify("\n".join(messages))

# Save cache
json.dump(new_ids, open(CACHE_FILE, "w"))
