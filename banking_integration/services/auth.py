import frappe
from frappe.utils import add_to_date, now_datetime
from banking_integration.clients.jenga import JengaClient


def authenticate():
    client = JengaClient()

    token = client.generate_token()

    settings = frappe.get_single("Jenga Credentials")
    settings.access_token = token
    settings.token_expiry = add_to_date(
        now_datetime(),
        minutes=55,
        as_datetime=True
    )
    settings.save(ignore_permissions=True)
    print("Saved token:", settings.access_token)
    frappe.db.commit()

    return token

def get_valid_token():
    settings = frappe.get_single("Jenga Credentials")

    if (
        not settings.access_token
        or not settings.token_expiry
        or settings.token_expiry <= now_datetime()
    ):
        authenticate()
        settings.reload()

    return settings.access_token