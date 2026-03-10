from src.utils import webdriver


def get_truecaptcha():
    url = "https://truecaptcha.org/profile.html"
    webdriver.get(url)
