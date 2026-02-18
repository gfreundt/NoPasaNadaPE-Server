from seleniumbase import sb_cdp, SB
from pyvirtualdisplay import Display
import math
import base64


def one():
    url = "https://consultavehicular.sunarp.gob.pe/consulta-vehicular"

    sb = sb_cdp.Chrome(
        url,
        incognito=True,
        headless=True,
        window_size="1920,1080",
        binary_location="/usr/bin/google-chrome",  # adjust if your path is different
    )

    sb.sleep(6)
    sb.solve_captcha()
    print("**1")

    sb.sleep(2)
    sb.type("#nroPlaca", "ARQ085")
    print("**2")
    sb.sleep(2)
    sb.click("button")
    print("**3")
    sb.sleep(10)
    print("**4")
    # 📸 Take screenshot (saved in current working directory)
    sb.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    sb.sleep(1)
    sb.save_full_page_screenshot("sunarp_result.png")
    print("**5")
    sb.driver.stop()
    print("**6")


def two():

    url = "https://consultavehicular.sunarp.gob.pe/consulta-vehicular"

    # Use the SB context manager for better resource management
    with SB(uc=True, headless=False) as sb:
        sb.activate_cdp_mode(url)  # Using CDP with UC is more powerful
        sb.set_window_size(1920, 1080)

        # 1. Initial wait for Cloudflare to challenge
        sb.sleep(8)

        # 2. Use the specialized UC captcha solver
        sb.uc_gui_click_captcha()

        print("** Captcha Solved")
        sb.sleep(2)

        # 3. Use stealth typing (simulates human keypresses)
        sb.type("#nroPlaca", "LIA118")
        print("** Plate entered")

        sb.sleep(1)
        sb.click("button")  # More specific selector

        print("** Button clicked")
        sb.sleep(10)

        cdp_full_page_png(sb, "sunarp_result.png")
        print("** Full page screenshot saved")


def three():

    url = "https://consultavehicular.sunarp.gob.pe/consulta-vehicular"

    print("***1")

    with Display(visible=0, size=(1920, 1080)):

        print("***2")

        # 2. Run SeleniumBase with headless=False (important!)
        # Because there is a virtual display, headless=False won't crash
        with SB(uc=True, headless=False) as sb:
            sb.activate_cdp_mode(url)

            print("Connected. Waiting for Cloudflare...")
            sb.sleep(8)

            # UC Mode's best way to handle the checkbox
            sb.uc_gui_click_captcha()

            sb.sleep(2)
            sb.type("#nroPlaca", "ARQ085")

            # Sometimes the button needs a scroll-to-view to look human
            sb.scroll_to("button")
            sb.click('button:contains("Consultar")')

            print("Query sent. Waiting for results...")
            sb.sleep(10)

            sb.save_screenshot("sunarp_result.png")
            print("Done! Screenshot saved.")

    # The display context manager automatically stops Xvfb here


def cdp_full_page_png(sb, filename: str):
    metrics = sb.execute_cdp_cmd("Page.getLayoutMetrics", {})
    content = metrics["contentSize"]
    width = math.ceil(content["width"])
    height = math.ceil(content["height"])

    sb.execute_cdp_cmd(
        "Emulation.setDeviceMetricsOverride",
        {
            "width": width,
            "height": height,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
    )

    shot = sb.execute_cdp_cmd(
        "Page.captureScreenshot",
        {
            "format": "png",
            "fromSurface": True,
            "captureBeyondViewport": True,
        },
    )

    with open(filename, "wb") as f:
        f.write(base64.b64decode(shot["data"]))

    sb.execute_cdp_cmd("Emulation.clearDeviceMetricsOverride", {})


two()
