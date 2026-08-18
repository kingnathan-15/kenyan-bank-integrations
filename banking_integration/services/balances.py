import frappe

from banking_integration.clients.jenga import JengaClient


def refresh_balance(bank_account):
    if isinstance(bank_account, str):
        bank_account = frappe.get_doc(
            "Bank Account",
            bank_account,
        )

    client = JengaClient(
        bank_account=bank_account,
    )

    response = client.get_balance(
        account_number=bank_account.bank_account_no,
        country_code=bank_account.custom_country_code,
    )

    balances = response.get(
        "data",
        {},
    ).get(
        "balances",
        [],
    )

    available_balance = next(
        (
            balance.get("amount")
            for balance in balances
            if balance.get("type") == "Available"
        ),
        0,
    )

    bank_account.custom_reported_balance = available_balance
    bank_account.custom_last_balance_sync = frappe.utils.now_datetime()

    bank_account.save(
        ignore_permissions=True,
    )

    return response