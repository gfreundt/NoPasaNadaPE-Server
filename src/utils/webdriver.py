import os
import platform
from selenium import webdriver
from seleniumwire import webdriver as sw_webdriver

# REMOVED: seleniumwire
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import subprocess
import json
from security.keys import PROXY_DATACENTER, PROXY_RESIDENTIAL
from src.utils.constants import NETWORK_PATH, CHROMEDRIVER_PATH


class ChromeUtils:
    def __init__(self, **kwargs):
        parameters = {
            "incognito": True,
            "headless": False,
            "window_size": False,
            "load_profile": False,
            "no_driver_update": False,
            "maximized": False,
            "proxy": False,
        } | kwargs

        if not parameters["no_driver_update"]:
            self.driver_update()

        self.options = Options()
        # Use log_path=os.devnull to keep your VPS logs clean
        self.service = Service(CHROMEDRIVER_PATH, log_path=os.devnull)

        prefs = {
            "download.default_directory": os.path.join(NETWORK_PATH, "static"),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "printing.print_preview_disabled": True,
            "savefile.default_directory": os.path.join(NETWORK_PATH, "static"),
            "printing.default_destination_selection_rules": {
                "kind": "local",
                "name": "Save as PDF",
            },
            "printing.print_preview_sticky_settings.appState": '{"recentDestinations":[{"id":"Save as PDF","origin":"local"}],"selectedDestinationId":"Save as PDF","version":2}',
            "safebrowsing.enabled": True,
        }
        self.options.add_experimental_option("prefs", prefs)

        # Standard VPS arguments
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        self.options.add_argument("--disable-gpu")

        if parameters["incognito"]:
            self.options.add_argument("--incognito")
        if parameters["headless"]:
            self.options.add_argument("--headless=new")
        if parameters["window_size"]:
            self.options.add_argument("--window-size=1920,1080")

        self.options.add_argument("--disable-blink-features=AutomationControlled")
        self.options.add_experimental_option(
            "excludeSwitches", ["enable-logging", "enable-automation"]
        )
        self.options.add_experimental_option("useAutomationExtension", False)
        self.options.add_argument(
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.7444.176 Safari/537.36"
        )

    def proxy_driver(self):
        username = "LcL8ujXtMohd3ODu"
        password = "Lm4lJIxiyRd9nNCp_country-pe"
        proxy_url = "geo.iproyal.com"
        proxy_url_port = "12321"

        proxy = f"http://{username}:{password}@{proxy_url}:{proxy_url_port}"

        # Configure options for Selenium Wire
        proxy_options = {
            "proxy": {
                "http": proxy,
                "https": proxy,
            },
            "disable_capture": False,
            "ssl_insecure": True,
        }

        # --- SELENIUM SETUP ---
        chrome_options = Options()
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-insecure-localhost")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.accept_insecure_certs = True

        # Initialize the WebDriver
        return sw_webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options,
            seleniumwire_options=proxy_options,
        )

    def direct_driver(self):
        return webdriver.Chrome(service=self.service, options=self.options)

    def driver_update(self, **kwargs):
        return
        """Compares current Chrome browser and Chrome driver versions and updates driver if necessary"""

        def check_chrome_version():
            result = subprocess.check_output(
                r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
            ).decode("utf-8")
            return result.split(" ")[-1].split(".")[0]

        def check_chromedriver_version():
            try:
                version = subprocess.check_output(f"{CURRENT_PATH} -v").decode("utf-8")
                return version.split(".")[0][-3:]
            except KeyboardInterrupt:
                return 0

        def download_chromedriver(target_version):
            # extract latest data from Google API
            api_data = json.loads(requests.get(GOOGLE_CHROMEDRIVER_API).text)

            # find latest build for current Chrome version and download zip file
            endpoints = api_data["milestones"][str(target_version)]["downloads"][
                "chromedriver"
            ]
            url = [i["url"] for i in endpoints if i["platform"] == "win64"][0]
            with open(TARGET_PATH, mode="wb") as download_file:
                download_file.write(requests.get(url).content)

            # delete current chromedriver.exe
            if os.path.exists(CURRENT_PATH):
                os.remove(CURRENT_PATH)

            # unzip downloaded file contents into Resources folder
            cmd = rf'Expand-Archive -Force -Path {TARGET_PATH} -DestinationPath "{BASE_PATH}"'
            subprocess.run(["powershell", "-Command", cmd])

            # move chromedriver.exe to correct folder
            os.rename(os.path.join(UNZIPPED_PATH, "chromedriver.exe"), CURRENT_PATH)

            # delete unnecesary files after unzipping
            os.remove(os.path.join(UNZIPPED_PATH, "LICENSE.chromedriver"))

        def file_cleanup(path):

            try:
                # erase downloaded zip file
                os.remove(TARGET_PATH)

                # erase files in unzipped folder and then erase folder
                _folder = os.path.join(path, "chromedriver-win64")
                for file in _folder:
                    os.remove(file)
                os.rmdir(_folder)

            except Exception:
                pass

        # define URIs
        GOOGLE_CHROMEDRIVER_API = "https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-milestone-with-downloads.json"
        if "Windows" in platform.uname().system:
            BASE_PATH = os.path.join("src")
        else:
            BASE_PATH = r"/home/gfreundt/pythonCode/Resources"

        CURRENT_PATH = os.path.join(BASE_PATH, "chromedriver.exe")
        TARGET_PATH = os.path.join(BASE_PATH, "chromedriver.zip")
        UNZIPPED_PATH = os.path.join(BASE_PATH, "chromedriver-win64")

        # get current browser and chromedriver versions
        driver = check_chromedriver_version()
        browser = check_chrome_version()

        # if versions don't match, get the correct chromedriver from repository
        if driver != browser:
            download_chromedriver(browser)
            print("*** Updated Chromedriver ***")
            # clean all unnecessary files
            file_cleanup(BASE_PATH)
