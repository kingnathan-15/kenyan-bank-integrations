import frappe

from frappe.utils import add_to_date, now_datetime

from banking_integration.clients.jenga import JengaClient


def authenticate(credentials):
    if isinstance(credentials, str):
        credentials = frappe.get_doc(
            "Bank Integration Credentials",
            credentials,
        )

    client = JengaClient(credentials)

    token = client.generate_token()

    credentials.access_token = token
    credentials.token_expiry = add_to_date(
        now_datetime(),
        minutes=55,
        as_datetime=True,
    )

    credentials.save(ignore_permissions=True)
    frappe.db.commit()

    return token


def get_valid_token(credentials):
    if isinstance(credentials, str):
        credentials = frappe.get_doc(
            "Bank Integration Credentials",
            credentials,
        )

    if (
        not credentials.access_token
        or not credentials.token_expiry
        or credentials.token_expiry <= now_datetime()
    ):
        return authenticate(credentials)

    return credentials.access_token