import frappe

from frappe.utils import today

from banking_integration.clients.jenga import JengaClient
from banking_integration.services.balances import refresh_balance
from banking_integration.utils.reference import generate_reference


def send_money(transfer: str):

    client = JengaClient()

    # Load the transfer document
    doc = frappe.get_doc("Bank Transfer", transfer)

    # Load linked Accounts documents
    source = frappe.get_doc("Accounts", doc.source_account)
    destination = frappe.get_doc("Accounts", doc.destination_account)

    # Mark as processing
    doc.status = "Processing"
    doc.save(ignore_permissions=True)

    # Generate transaction reference
    reference = generate_reference()
    doc.transaction_reference = reference

    # Refresh balances before transfer
    refresh_balance(source)
    refresh_balance(destination)

    doc.source_balance_before = source.current_balance
    doc.destination_balance_before = destination.current_balance

    # Build payload
    payload = {
        "source": {
            "countryCode": source.country_code,
            "name": source.account_name,
            "accountNumber": source.account_number,
        },
        "destination": {
            "type": "bank",
            "countryCode": destination.country_code,
            "name": destination.account_name,
            "accountNumber": destination.account_number,
        },
        "transfer": {
            "type": doc.transfer_type,
            "amount": str(doc.amount),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }

    # Store request payload
    doc.request_json = frappe.as_json(payload, indent=4)

    try:
        response = client.internal_bank_transfer(payload)

        doc.response_json = frappe.as_json(response, indent=4)
        doc.bank_reference = response.get("reference")

        if response.get("status") is True:
            doc.status = "Successful"

            refresh_balance(source)
            refresh_balance(destination)

            doc.source_balance_after = source.current_balance
            doc.destination_balance_after = destination.current_balance

        else:
            doc.status = "Failed"

            frappe.throw(
                response.get(
                    "message",
                    "Transfer failed."
                )
            )

    except Exception as e:
        doc.status = "Failed"
        doc.response_json = str(e)
        raise

    finally:
        doc.save(ignore_permissions=True)

    return doc