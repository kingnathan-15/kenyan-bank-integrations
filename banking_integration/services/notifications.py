import frappe
from frappe.utils import now_datetime


def process_notification(notification_type, payload):
    """
    Entry point for all incoming Jenga webhook notifications.
    """

    log = create_notification_log(notification_type, payload)

    try:
        process_business_logic(
            notification_type=notification_type,
            payload=payload,
            log=log,
        )

        log.status = "Processed"
        log.processed = 1

    except Exception:
        log.status = "Failed"
        log.error = frappe.get_traceback()

        frappe.log_error(
            title=f"{notification_type} Processing Failed",
            message=frappe.get_traceback(),
        )

    log.save(ignore_permissions=True)

    return {
        "status": "received"
    }


def create_notification_log(notification_type, payload):

    log = frappe.new_doc("Jenga Notification Log")

    log.notification_type = notification_type
    log.received_on = now_datetime()
    log.payload = frappe.as_json(payload, indent=2)
    log.status = "Received"

    log.insert(ignore_permissions=True)

    return log


def process_business_logic(notification_type, payload, log):
    """
    Dispatch notification to the appropriate handler.
    """

    handlers = {
        "Credit Alert": process_credit_alert,
        "Deposit Notification": process_deposit_notification,
        "Payment Confirmation": process_payment_confirmation,
        "Transaction Status": process_transaction_status,
    }

    handler = handlers.get(notification_type)

    if not handler:
        raise ValueError(f"Unsupported notification type: {notification_type}")

    handler(payload, log)


def process_credit_alert(payload, log):
    """
    Handle credit alert notifications.
    """

    log.reference = payload.get("reference")
    log.status = "Received"


def process_deposit_notification(payload, log):
    """
    Handle deposit notifications.
    """

    log.reference = payload.get("reference")
    log.status = "Received"



def process_payment_confirmation(payload, log):
    """
    Handle payment confirmation notifications.
    """

    log.reference = payload.get("reference")
    log.status = "Received"



def process_transaction_status(payload, log):
    """
    Handle transfer status updates.
    """

    log.reference = payload.get("reference")
    log.status = "Received"