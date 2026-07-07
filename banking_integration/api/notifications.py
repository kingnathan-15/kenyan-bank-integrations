import frappe

from banking_integration.services.notifications import process_notification


@frappe.whitelist(allow_guest=True)
def credit_alert():

    payload = frappe.request.get_json()

    return process_notification(
        notification_type="Credit Alert",
        payload=payload
    )


@frappe.whitelist(allow_guest=True)
def deposit_notification():

    payload = frappe.request.get_json()

    return process_notification(
        notification_type="Deposit Notification",
        payload=payload
    )


@frappe.whitelist(allow_guest=True)
def payment_confirmation():

    payload = frappe.request.get_json()

    return process_notification(
        notification_type="Payment Confirmation",
        payload=payload
    )


@frappe.whitelist(allow_guest=True)
def transaction_status():

    payload = frappe.request.get_json()

    return process_notification(
        notification_type="Transaction Status",
        payload=payload
    )