import frappe

from banking_integration.services.auth import authenticate
from banking_integration.services.balances import refresh_balance
from banking_integration.services.providers import (
    get_bank_account_credentials,
)
from banking_integration.services.reconciliation import reconcile_statement
from banking_integration.services.statements import sync_stanbic_statement


@frappe.whitelist(allow_guest=True)
def ipn():
    try:
        payload = frappe.request.get_json(silent=True)

        if payload is None:
            payload = frappe.request.form.to_dict()

        if not payload:
            payload = {
                "raw_body": frappe.request.get_data(as_text=True)
            }

        frappe.log_error(
            title="Stanbic IPN Received",
            message=frappe.as_json({
                "method": frappe.request.method,
                "content_type": frappe.request.content_type,
                "payload": payload,
            }, indent=2),
        )

        return {
            "status": "success"
        }

    except Exception:
        frappe.log_error(
            title="Stanbic IPN Error",
            message=frappe.get_traceback(),
        )

        return {
            "status": "error"
        }
    
@frappe.whitelist(allow_guest=True)
def fetch_statements(account, from_date, to_date):
    result = sync_stanbic_statement(
        account,
        from_date,
        to_date,
    )

    return result

@frappe.whitelist()
def authenticate_stanbic():
    credentials = get_provider_credentials("Stanbic")

    client = StanbicClient(credentials)

    token = client.get_access_token(force_refresh=True)

    return {
        "success": True,
        "message": "Stanbic authentication successful",
        "expires_at": credentials.token_expiry,
    }


@frappe.whitelist()
def reconcile_account_statement(statement):
    return reconcile_statement(statement)


@frappe.whitelist()
def bulk_reconcile_account_statements(bank=None):
    filters = {
        "reconciliation_status": ["!=", "Matched"]
    }

    statements = frappe.get_all(
        "Account Statement",
        filters=filters,
        fields=["name", "account"],
    )

    result = {
        "total": 0,
        "matched": 0,
        "unmatched": 0,
        "multiple_matches": 0,
        "already_matched": 0,
        "errors": 0,
    }

    # Resolve selected bank to actual ERPNext Bank name
    if bank and bank != "All Banks":
        bank_name = frappe.db.get_value(
            "Bank",
            {"name": ["like", f"%{bank}%"]},
            "name",
        )
    else:
        bank_name = None

    for statement in statements:

        if bank_name:
            statement_bank = frappe.db.get_value(
                "Bank Account",
                statement.account,
                "bank",
            )

            if statement_bank != bank_name:
                continue

        result["total"] += 1

        try:
            outcome = reconcile_account_statement(
                statement=statement.name
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
            result["errors"] += 1

            frappe.log_error(
                frappe.get_traceback(),
                "Stanbic Bulk Reconciliation",
            )

    frappe.db.commit()

    return result