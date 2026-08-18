import frappe
from frappe import _

from banking_integration.clients.jenga import JengaClient


@frappe.whitelist()
def refresh_balance(bank_account):
    doc = frappe.get_doc("Bank Account", bank_account)

    if not doc.bank_account_no:
        frappe.throw(_("Bank Account Number is required."))

    client = JengaClient(bank_account=doc)

    result = client.get_balance(doc.bank_account_no)

    balances = result.get("data", {}).get("balances", [])

    balance = None

    for item in balances:
        if item.get("type") == "Available":
            balance = float(item.get("amount", 0))
            break

    if balance is None and balances:
        balance = float(balances[0].get("amount", 0))

    if balance is None:
        frappe.throw(
            _("Could not find balance in bank API response.")
        )

    doc.custom_reported_balance = balance
    doc.save(ignore_permissions=True)

    return {
        "account": doc.name,
        "balance": balance,
        "currency": result.get("data", {}).get("currency"),
        "response": result,
    }