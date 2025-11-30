import time
import requests
import json
import smtplib
import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

API_URL = "https://mosaic-plaza-aanbodapi.zig365.nl/api/v1/actueel-aanbod?limit=60&locale=en_GB&page=0&sort=+reactionData.aangepasteTotaleHuurprijs"

CACHE_FILE = "plaza_cache_auto.json"

EMAIL = os.environ["BOT_EMAIL"]
PASSWORD = os.environ["BOT_PASSWORD"]
TO_1 = os.environ["BOT_TO"]
TO_2 = os.environ["BOT_TO_2"]

PLAZA_USERNAME = os.environ["PLAZA_USERNAME"]
PLAZA_PASSWORD = os.environ["PLAZA_PASSWORD"]


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
def fetch_new_listings():
    try:
        data = requests.get(API_URL, timeout=10).json()
    except Exception:
        return []

    if "data" not in data:
        return []

    listings = [
        item for item in data["data"]
        if item.get("gemeenteGeoLocatieNaam") == "Delft"
        and item.get("rentBuy") == "Huur"
        and isinstance(item.get("totalRent"), (int, float))
        and item.get("totalRent") > 100
    ]
    try: 
        old_ids = json.load(open(CACHE_FILE))
    except:
        old_ids = []

    new = [item for item in listings if item["id"] not in old_ids]

    # Save full list for next run
    json.dump([item["id"] for item in listings], open(CACHE_FILE, "w"))

    return new

# Selenium
def create_driver():
    print("in create_driver method")
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    return webdriver.Chrome(options=opts)
    
def expand_shadow(driver, host):
    return driver.execute_script("return arguments[0].shadowRoot", host)

# -------------------------------------------------------------
# LOGIN
# -------------------------------------------------------------
def login(driver):
    print("DEBUG: Opening home page…")
    driver.get("https://plaza.newnewnew.space/")
    time.sleep(1)
    # Accept cookies if present
    try:
        WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Akkoord') or contains(., 'Agree')]"))).click()
        print("DEBUG: Cookie popup dismissed")
    except:
        pass
    print("DEBUG: Clicking INLOGGEN…")
    try:
        login_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(., 'Inloggen')]")))
        login_btn.click()
        print("Clicked login button")
    except Exception as e:
        print("DEBUG ERROR: Could not click Inloggen:", e)
        driver.save_screenshot("debug_login_fail.png")
        raise

    time.sleep(1)
    
    username_host = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "zds-input-text[name='username']")))
    username_shadow = expand_shadow(driver, username_host)
    print("after username_shadow = get shadow")
    username_input = username_shadow.find_element(By.CSS_SELECTOR, "input")
    username_input.send_keys(PLAZA_USERNAME)
    print("typed username")
    
    password_host = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "zds-input-text[name='password']")))
    password_shadow = expand_shadow(driver, password_host)
    password_input = password_shadow.find_element(By.CSS_SELECTOR, "input")
    password_input.send_keys(PLAZA_PASSWORD)
    print("Typed password")

    # --- SUBMIT BUTTON ---
    submit_host = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "zds-button[type='submit']")))
    driver.execute_script("arguments[0].scrollIntoView(true);", submit_host)
    time.sleep(0.3)
    submit_host.click()
    print("Clicked login submit host")
    # Wait for redirect
    WebDriverWait(driver, 25).until(EC.url_contains("portaal"))

# -------------------------------------------------------------
# APPLY
# -------------------------------------------------------------
def apply_to_listing(driver, item):
    url = f"https://plaza.newnewnew.space/aanbod/huurwoningen/details/{item.get('urlKey')}"
    driver.get(url)

    try:
        btn = WebDriverWait(driver, 15).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.reageer-button")))
    except:
        return False, "React button not found"
    btn.click()

    try:
        popup = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".mfp-content")))
    except:
        return False, "No confirmation popup"

    if "Bedankt voor je reactie" in popup.text:
        return True, "Successfully applied"
    else:
        return False, f"Popup text unexpected: {popup.text}"
        
# -------------------------------------------------------------
# MAIN LOGIC
# -------------------------------------------------------------
def main():
    print("Bot started (loop mode)")
    while True:
        try:      
            new_listings = fetch_new_listings()
            if not new_listings:
                print("No new listings")
                continue
            driver = create_driver()
            try:
                login(driver)
                print("Logged in")
            except Exception as e:
                notify(f"Login failed: {e}")
                driver.quit()
                continue
            results = []
            for item in new_listings:
                ok, msg = apply_to_listing(driver, item)
                listing_id = item["id"]
                if ok:
                    results.append(f"Applied successfully for listing {listing_id}")
                else:
                    results.append(f"Apply failed for listing {listing_id}: {msg}")
            driver.quit()
            notify("\n".join(results))

        except Exception as e:
            notify(f"Bot crashed: {e}")
        time.sleep(15) # check every 15 seconds
    
    
print("Before Main")
if __name__ == "__main__":
    main()
print("After main")
