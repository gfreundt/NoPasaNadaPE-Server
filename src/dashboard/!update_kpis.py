import requests

# from google.cloud import billingbudgets_v1
from security.keys import (
    TRUECAPTCHA_API_KEY,
    TWOCAPTCHA_API_KEY,
)


def get_nopasanadape():
    try:
        url = "https://nopasanadape.com"
        r = requests.get(url)
        if r.status_code == 200:
            return "✅ ONLINE"
        else:
            return "❌ PROBLEMAS"

    except requests.exceptions.RequestException:
        return "❓ N/A"


def get_truecaptcha():
    try:
        url = rf"https://api.apiTruecaptcha.org/one/hello?method=get_all_user_data&userid=gabfre%40gmail.com&apikey={TRUECAPTCHA_API_KEY}"
        r = requests.get(url, timeout=5)
        return f"✅ USD {r.json()['data']['get_user_info'][4]['value']:.2f}"
    except Exception:
        return "❓ N/A"


def get_zeptomail():
    return "❓ N/A"


def get_brightdata():
    return 0
    # BALANCE_URL = "https://api.brightdata.com/balance"
    # headers = {
    #     "Authorization": f"Bearer {BRIGHT_DATA_API_KEY}",
    #     "Content-Type": "application/json",
    # }
    # try:
    #     response = requests.get(BALANCE_URL, headers=headers, timeout=5)
    #     if response.status_code == 200:
    #         balance_data = response.json()
    #         balance = balance_data.get("balance")
    #         if balance:
    #             return f"✅ USD {balance}"

    #     return "❓ N/A"

    # except requests.exceptions.RequestException:
    #     return "❓ N/A"


def get_googlecloud():
    return "❓ N/A"

    # client = billingbudgets_v1.BudgetServiceClient()
    # name = f"billingAccounts/{GC_BILLING_ACCOUNT_ID}/budgets/{GC_BUDGET_ID}"

    # try:
    #     budget = client.get_budget(name=name)
    #     if budget.amount.last_period_amount is not None:
    #         summary = budget.budgeted_amount_summary
    #         spend_money = summary.current_budget_spend
    #         actual_spend = spend_money.units + spend_money.nanos / 1e9
    #         currency = spend_money.currency_code
    #         return f"{currency} {actual_spend:.2f}"
    #     else:
    #         return "⚠️ N/A"

    # except Exception:
    #     return "❓ N/A"


def get_2captcha():
    URL = f"https://2captcha.com/res.php?key={TWOCAPTCHA_API_KEY}&action=getbalance"

    try:
        response = requests.get(URL, timeout=5)
        response.raise_for_status()
        result = response.text

        if result.startswith("ERROR_"):
            return "❓ N/A"
        else:
            try:
                balance = float(result)
                return f"✅ USD {balance:.2f}"
            except ValueError:
                return "❓ N/A"

    except requests.exceptions.RequestException:
        return "❓ N/A"


def get_cloudfare():
    status_api_url = "https://www.cloudflarestatus.com/api/v2/status.json"
    try:
        response = requests.get(status_api_url, timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes
        status_data = response.json()
        indicator = status_data.get("status", {}).get("indicator", "unknown")

        if indicator in ["major", "critical"]:
            return "❌ INACTIVO"
            # Add your custom logic here (e.g., switch to a backup server)
        elif indicator == "minor":
            return "⚠️ ACTIVO"
        elif indicator is not None:
            return "✅ ACTIVO"
        else:
            return "❓ N/A"

    except requests.exceptions.RequestException:
        return "❓ N/A"


def main(self):
    """actualiza la variable de Dashboard con el resultado de las consultas
    de saldos/status de los servicios usados cada cierto tiempo"""

    kpis = {
        "kpi_nopasanadape_status": get_nopasanadape(),
        "kpi_truecaptcha_balance": get_truecaptcha(),
        "kpi_zeptomail_balance": get_zeptomail(),
        "kpi_brightdata_balance": get_brightdata(),
        "kpi_twocaptcha_balance": get_2captcha(),
        "kpi_googlecloud_balance": get_googlecloud(),
        "kpi_cloudfare_status": get_cloudfare(),
    }
    self.data.update(kpis)
