import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

KUNDALIK_URL = "https://kundalik.com"
LOGIN_URL = "https://kundalik.com/login"
WAIT_TIMEOUT = 15
ACTIVE_WAIT = 3  # seconds to stay on profile page


def _make_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")           # Docker uchun muhim
    options.add_argument("--disable-dev-shm-usage") # Docker uchun muhim
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--remote-debugging-port=9222")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # ChromeDriver yo'lini avtomatik topish yoki /usr/local/bin/chromedriver
    from selenium.webdriver.chrome.service import Service
    chromedriver_path = "/usr/local/bin/chromedriver"
    if os.path.exists(chromedriver_path):
        service = Service(chromedriver_path)
        driver = webdriver.Chrome(service=service, options=options)
    else:
        # Lokal ishlab chiqishda webdriver-manager ishlatiladi
        from webdriver_manager.chrome import ChromeDriverManager
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def _login_and_wait(driver: webdriver.Chrome, login: str, password: str) -> bool:
    """Opens Kundalik login page, logs in, waits, then logs out. Returns True on success."""
    try:
        driver.get(LOGIN_URL)
        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        # Find username field
        username_input = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_input.clear()
        username_input.send_keys(login)

        # Find password field
        password_input = driver.find_element(By.NAME, "password")
        password_input.clear()
        password_input.send_keys(password)

        # Submit form
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # Wait until redirected away from login page
        wait.until(EC.url_changes(LOGIN_URL))

        # Stay active for a few seconds so system registers activity
        time.sleep(ACTIVE_WAIT)

        # Logout — try common logout paths
        logout_success = False
        for logout_url in [
            f"{KUNDALIK_URL}/logout",
            f"{KUNDALIK_URL}/auth/logout",
        ]:
            try:
                driver.get(logout_url)
                time.sleep(1)
                logout_success = True
                break
            except Exception:
                continue

        if not logout_success:
            # Try clicking logout button if redirect didn't work
            try:
                logout_btn = driver.find_element(
                    By.CSS_SELECTOR, "a[href*='logout'], button[class*='logout']"
                )
                logout_btn.click()
                time.sleep(1)
            except NoSuchElementException:
                pass  # Already logged out or different flow

        return True

    except TimeoutException:
        logger.warning(f"Timeout for login: {login}")
        return False
    except Exception as e:
        logger.error(f"Error for login {login}: {e}")
        return False


def make_all_online(students: list, progress_callback=None) -> dict:
    """
    Iterates over all students, logs in as student then as parent.
    progress_callback(current, total, fio, who, success) called after each step.
    Returns summary dict.
    """
    total = len(students)
    results = {
        "total_students": total,
        "student_ok": 0,
        "student_fail": 0,
        "parent_ok": 0,
        "parent_fail": 0,
    }

    driver = _make_driver()
    try:
        for idx, student in enumerate(students, 1):
            fio = student.get("fio", student["login"])

            # --- Student login ---
            ok = _login_and_wait(driver, student["login"], student["password"])
            if ok:
                results["student_ok"] += 1
            else:
                results["student_fail"] += 1
            if progress_callback:
                progress_callback(idx, total, fio, "o'quvchi", ok)

            # --- Parent login ---
            parent = student.get("parent", {})
            if parent.get("login") and parent.get("password"):
                ok_p = _login_and_wait(driver, parent["login"], parent["password"])
                if ok_p:
                    results["parent_ok"] += 1
                else:
                    results["parent_fail"] += 1
                if progress_callback:
                    progress_callback(idx, total, fio, "ota-ona", ok_p)

    finally:
        driver.quit()

    return results
