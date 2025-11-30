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

    return webdriver.Chrome(options=opts)

# -------------------------------------------------------------
# LOGIN
# -------------------------------------------------------------
def login(driver):
    print("DEBUG: Opening home page…")
    driver.get("https://plaza.newnewnew.space/")
    time.sleep(2)
    print("DEBUG: Page title =", driver.title)
    print("DEBUG: Clicking login button…")
    # Try dismissing cookie banner
    try:
        accept_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Akkoord') or contains(., 'Agree')]"))
        )
        accept_btn.click()
        print("DEBUG: Cookie banner dismissed")
    except:
        pass  # No cookie banner
        
    try:
        login_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Inloggen') or contains(., 'Login')]")))
        login_btn.click()
    except:
        try:
            menu_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button.menu-toggle, .menu-toggle")))
            menu_btn.click()
            print("found menu_btn")
            time.sleep(1)
            login_btn = WebDriverWait(driver, 8).until(EC.element_to_be_clickable((By.XPATH, "//a[contains(., 'Inloggen') or contains(., 'Login')]")))
            login_btn.click()
        except Exception as e:
            print("DEBUG ERROR: Could not click login button:", e)
            driver.save_screenshot("debug_no_login_button.png")
            raise
        time.sleep(2)
        print("DEBUG: Current URL after clicking =", driver.current_url)

    # DEBUG: Dump page HTML to inspect
    html = driver.page_source
    open("debug_login_html.html", "w", encoding="utf-8").write(html)
    print("DEBUG: Saved page to debug_login_html.html")

    try:
        user_field = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.NAME, "tx_felogin_pi1[username]")))
    except Exception as e:
        print("DEBUG ERROR: Username field not found:", e)
        driver.save_screenshot("debug_no_username_field.png")
        raise
    user_field.send_keys(PLAZA_USERNAME)
    driver.find_element(By.NAME, "tx_felogin_pi1[password]").send_keys(PLAZA_PASSWORD)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()

    print("DEBUG: Submitted login")
    try:
        WebDriverWait(driver, 20).until(EC.url_contains("portaal"))
    except:
        print("DEBUG ERROR: Login did not redirect correctly")
        driver.save_screenshot("debug_login_failed.png")
        raise

    print("DEBUG: Login SUCCESSFUL. URL =", driver.current_url)


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
    print("Entered main")
    new_listings = fetch_new_listings()
    if not new_listings:
        print("No new listings")
        return
    driver = create_driver()
    try:
        login(driver)
        print("Logged in")
    except Exception as e:
        notify(f"Login failed: {e}")
        driver.quit()
        return
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
    
print("Before Main")
if __name__ == "__main__":
    main()
print("After main")
