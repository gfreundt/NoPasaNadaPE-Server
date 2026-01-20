import time
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException


# --- NEW: REQUEST INTERCEPTOR FUNCTION ---
def force_https_interceptor(request):
    """Checks the request URL and forces the scheme to be HTTPS if it is HTTP."""
    if request.url.startswith("http://") and not request.url.startswith(
        "http://127.0.0.1"
    ):
        request.url = request.url.replace("http://", "https://", 1)


def test():
    # --- PROXY CREDENTIALS (Using your provided values) ---
    username = "LcL8ujXtMohd3ODu"
    password = "Lm4lJIxiyRd9nNCp_country-pe"
    proxy_url = "geo.iproyal.com"
    proxy_url_port = "12321"

    PAGE_LOAD_TIMEOUT = 30

    proxy = f"http://{username}:{password}@{proxy_url}:{proxy_url_port}"

    # Configure options for Selenium Wire
    proxy_options = {
        "proxy": {
            "http": proxy,
            "https": proxy,
        },
        # Ensure all requests are recorded
        "disable_capture": False,
        "ssl_insecure": True,
    }

    # --- SELENIUM SETUP ---
    chrome_options = Options()
    # AGGRESSIVE FLAGS TO BYPASS SSL WARNINGS (Keep these)
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--allow-insecure-localhost")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.accept_insecure_certs = True

    # Standard User Agent (Keep this)
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # Initialize the WebDriver
    try:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
            seleniumwire_options=proxy_options,
        )
    except WebDriverException as e:
        print(f"Error initializing WebDriver: {e}")
        return  # Exit if driver fails to start

    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
    print(f"Set page load timeout to {PAGE_LOAD_TIMEOUT} seconds.")

    # --- APPLY THE HTTPS INTERCEPTOR ---
    driver.request_interceptor = force_https_interceptor
    print("HTTPS Interceptor applied successfully.")

    TARGET_URL = "https://licencias.mtc.gob.pe/#/index"

    try:
        # 1. Navigate to the target site with a timeout
        print(f"Attempting to load {TARGET_URL}...")
        driver.get(TARGET_URL)

        print(f"--- Successfully loaded (Full Page): {driver.title} ---")

    except TimeoutException:
        print(
            f"--- WARNING: Page load timed out after {PAGE_LOAD_TIMEOUT} seconds. ---"
        )
        print(
            f"--- Script proceeding with partially loaded page: {driver.current_url} ---"
        )
        time.sleep(5)

    except Exception as e:
        print(f"\nAn unexpected error occurred during page load: {e}")
        return

    # --- START SCRAPING (Runs regardless of whether it timed out or fully loaded) ---
    try:
        # 2. ROBUST PROXY VERIFICATION
        print("\n--- Proxy Verification ---")

        # Check if any requests were captured
        if not driver.requests:
            print("WARNING: No network requests captured by Selenium Wire.")
        else:
            # Check the initial request for scheme
            initial_request = driver.requests[0]
            print(f"Initial Request URL Scheme: {initial_request.url.split(':')[0]}")

            # Iterate through the captured requests to find the first one that successfully routed via proxy
            proxy_detected = False
            for req in driver.requests:
                # The 'proxy' attribute should only exist if the request was routed via the proxy.
                if hasattr(req, "proxy") and req.proxy:
                    print(f"SUCCESS: Proxy detected on request to: {req.host}")
                    proxy_detected = True
                    break

            if not proxy_detected:
                print("WARNING: Proxy attribute not found in any captured request.")

        # 3. SAMPLE SCRAPING TASK
        print("\n--- Sample Scrape: Extracting Titles ---")

        # Alicorp may use different selectors, let's try a common heading:
        headings = driver.find_elements("xpath", "//h1 | //h2 | //h3")

        if headings:
            valid_headings = [h.text.strip() for h in headings if h.text.strip()]
            print(f"Found {len(valid_headings)} potential headings:")
            for i, heading in enumerate(valid_headings[:5]):
                print(f"{i+1}. {heading}")
        else:
            print("No general headings found.")

    except Exception as e:
        print(f"\nAn error occurred during scraping/verification: {e}")

    finally:
        driver.quit()
        print("\nScript finished and WebDriver closed.")


if __name__ == "__main__":
    test()
    time.sleep(300)
