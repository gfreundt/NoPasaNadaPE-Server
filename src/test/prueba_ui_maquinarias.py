from seleniumbase import SB


def main():
    url = "https://nopasanadape.com"
    with SB() as sb:
        sb.open("https://www.google.com")
