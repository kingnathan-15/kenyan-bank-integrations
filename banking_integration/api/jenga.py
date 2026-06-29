import frappe

from banking_integration.services.auth import authenticate
from banking_integration.services.balances import refresh_balance


@frappe.whitelist()
def test_connection():
    token = authenticate()

    return {
        "success": True,
        "token": token,
    }


@frappe.whitelist()
def get_account_balance(account: str):
    return refresh_balance(account)