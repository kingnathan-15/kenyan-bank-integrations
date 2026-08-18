import json

import frappe
from frappe import request
from werkzeug.wrappers import Response


def json_response(data, status=200):
    return Response(
        response=json.dumps(data),
        status=status,
        content_type="application/json",
    )


def get_payload():
    """Return the incoming request payload regardless of content type."""

    if request.is_json:
        return request.get_json(silent=True) or {}

    raw = request.get_data(as_text=True)

    if raw:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    return dict(frappe.form_dict)


def log_callback(callback_type, payload):
    """Store callback information for debugging."""

    headers = dict(request.headers)

    frappe.logger("kcb").info({
        "callback_type": callback_type,
        "method": request.method,
        "headers": headers,
        "payload": payload,
    })

    try:
        frappe.get_doc({
            "doctype": "Bank Callback Log",
            "callback_type": callback_type,
            "transaction_reference": (
                payload.get("transactionReference")
                or payload.get("retrievalRefNumber")
                or payload.get("reference")
            ),
            "payload": json.dumps(payload, indent=2),
            "headers": json.dumps(headers, indent=2),
        }).insert(ignore_permissions=True)

        frappe.db.commit()

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Failed to create Bank Callback Log"
        )


def update_bank_transfer(payload):
    """Update an existing Bank Transfer if found."""

    reference = (
        payload.get("transactionReference")
        or payload.get("retrievalRefNumber")
        or payload.get("reference")
    )

    if not reference:
        return

    transfer = frappe.db.exists(
        "Bank Transfer",
        {"transaction_reference": reference},
    )

    if not transfer:
        return

    doc = frappe.get_doc("Bank Transfer", transfer)

    if payload.get("status"):
        doc.status = payload["status"]

    if payload.get("statusDescription"):
        doc.status_description = payload["statusDescription"]

    if hasattr(doc, "callback_payload"):
        doc.callback_payload = json.dumps(payload, indent=2)

    doc.save(ignore_permissions=True)
    frappe.db.commit()


@frappe.whitelist(allow_guest=True)
def funds_transfer_callback():
    """KCB Funds Transfer callback endpoint."""

    try:
        payload = get_payload()

        log_callback("Funds Transfer", payload)
        update_bank_transfer(payload)

        return json_response({
            "success": True,
            "message": "Funds Transfer callback received"
        })

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "KCB Funds Transfer Callback"
        )

        return json_response({
            "success": False,
            "message": "Internal server error"
        }, status=500)


@frappe.whitelist(allow_guest=True)
def ipn():
    """KCB Instant Payment Notification endpoint."""

    try:
        payload = get_payload()

        log_callback("IPN", payload)

        # Future processing goes here
        # Example:
        # if payload.get("event") == "ACCOUNT_CREDIT":
        #     ...

        return json_response({
            "success": True,
            "message": "IPN received"
        })

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "KCB IPN Callback"
        )

        return json_response({
            "success": False,
            "message": "Internal server error"
        }, status=500)