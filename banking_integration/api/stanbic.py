import frappe

from banking_integration.services.auth import authenticate
from banking_integration.services.balances import refresh_balance
from banking_integration.services.providers import (
    get_bank_account_credentials,
)

@frappe.whitelist(allow_guest=True)
def ipn():


    try:
        payload = frappe.request.get_json(
            silent=True
        )

        if payload is None:
            payload = frappe.request.form.to_dict()

        if not payload:
            payload = {
                "raw_body": frappe.request.get_data(
                    as_text=True
                )
            }

        frappe.log_error(
            title="Stanbic IPN Received",
            message=frappe.as_json(
                payload,
                indent=2,
            ),
        )

        return {
            "status": "success"
        }

    except Exception as e:

        frappe.log_error(
            title="Stanbic IPN Error",
            message=frappe.get_traceback(),
        )

        return {
            "status": "error",
            "message": str(e),
        }

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