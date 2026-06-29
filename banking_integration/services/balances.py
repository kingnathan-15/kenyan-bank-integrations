import frappe

from banking_integration.clients.jenga import JengaClient

def refresh_balance(bank_account):

    if isinstance(bank_account, str):
        bank_account = frappe.get_doc("Accounts", bank_account)

    client = JengaClient()

    response = client.get_balance(
        account_number=bank_account.account_number,
        country_code=bank_account.country_code,
    )

    balances = response.get("data", {}).get("balances", [])

    available = None
    current = None

    for b in balances:
        if b.get("type", "").lower() == "available":
            available = float(b.get("amount"))
        elif b.get("type", "").lower() == "current":
            current = float(b.get("amount"))

    bank_account.current_balance = available
    bank_account.last_synced = frappe.utils.now_datetime()

    bank_account.save(ignore_permissions=True)

    return response