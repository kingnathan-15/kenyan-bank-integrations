import frappe

from banking_integration.services.auth import authenticate
from banking_integration.services.balances import refresh_balance
from banking_integration.services.providers import (
    get_bank_account_credentials,
)
from banking_integration.services.reconciliation import reconcile_statement
from banking_integration.services.statements import sync_jenga_statement
from banking_integration.services.transfers import send_money


@frappe.whitelist()
def test_connection(account: str):
    bank_account = frappe.get_doc(
        "Bank Account",
        account,
    )

    credentials = get_bank_account_credentials(
        bank_account,
    )

    token = authenticate(credentials)

    return {
        "success": True,
        "provider": bank_account.bank,
        "token": token,
    }


@frappe.whitelist()
def get_account_balance(account: str):
    return refresh_balance(account)


@frappe.whitelist()
def send_transfer(transfer: str):
    return send_money(transfer)

@frappe.whitelist()
def import_jenga_statement(
    account,
    from_date,
    to_date,
):
    result = sync_jenga_statement(
        bank_account=account,
        from_date=from_date,
        to_date=to_date,
    )

    return result


@frappe.whitelist()
def reconcile_account_statement(statement):
    return reconcile_statement(statement)

@frappe.whitelist()
def bulk_reconcile_statements():
    statements = frappe.get_all(
        "Account Statement",
        filters={
            "reconciliation_status": ["!=", "Matched"]
        },
        pluck="name",
    )

    result = {
        "processed": 0,
        "matched": 0,
        "unmatched": 0,
        "multiple_matches": 0,
        "already_matched": 0,
    }

    for name in statements:
        result["processed"] += 1

        try:
            outcome = reconcile_account_statement(
                statement=name
            )

            status = outcome.get("status")

            if status == "matched":
                result["matched"] += 1

            elif status == "unmatched":
                result["unmatched"] += 1

            elif status == "multiple_matches":
                result["multiple_matches"] += 1

            elif status == "already_matched":
                result["already_matched"] += 1

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Bulk Account Statement Reconciliation",
            )

            result["unmatched"] += 1

    frappe.db.commit()

    return result