import frappe

from banking_integration.services.auth import authenticate
from banking_integration.services.balances import refresh_balance
from banking_integration.services.transfers import send_money


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

@frappe.whitelist()
def send_transfer(transfer: str):
    return send_money(transfer)