import requests, json, smtplib, os

API_URL = "https://www.verra.nl/en/realtime-listings/consumer"
CACHE_FILE = "cache.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_EMAIL = os.environ["BOT_TO"]

def fetch_ids():
    url = "https://www.verra.nl/en/listings"
    html = requests.get(url).text

    # Debug raw HTML
    print("DEBUG RAW HTML:")
    print(html[:1500])

    soup = BeautifulSoup(html, "html.parser")

    script_tag = soup.find("script", {"class": "realtime-listings-json"})

    if not script_tag:
        print("ERROR: Could not find JSON script tag")
        return []

    try:
        data = json.loads(script_tag.text)
        print("DEBUG JSON:")
        print(json.dumps(data, indent=2)[:1500])
    except Exception as e:
        print("JSON PARSE ERROR:", e)
        return []

    # now data is a list of listing objects
    ids = [item["id"] for item in data]

    return ids

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
