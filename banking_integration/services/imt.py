import json

import frappe
from frappe.utils import today

from banking_integration.clients.jenga import JengaClient
from banking_integration.services.balances import refresh_balance
from banking_integration.utils.reference import generate_reference


def send_imt(docname):
    doc = frappe.get_doc("IMT Transfer", docname)
    client = JengaClient()

    source = frappe.get_doc("Accounts", doc.source_account)

    source_before = source.current_balance

    payload = build_payload(doc, source)

    doc.reference = payload["transfer"]["reference"]
    doc.request_json = json.dumps(payload, indent=2)
    doc.status = "Processing"
    doc.save(ignore_permissions=True)

    try:
        print(json.dumps(payload, indent=2))
        print(doc.recipient_account_number)
        response = client.send_transfer(payload)

        doc.response_json = json.dumps(response, indent=2)

        if response.get("status") is True:

            refresh_balance(source)

            source.reload()

            doc.source_balance_before = source_before
            doc.source_balance_after = source.current_balance

            doc.status = "Successful"

        else:

            doc.status = "Failed"

        if response.get("reference"):
            doc.bank_reference = response["reference"]

        if response.get("message"):
            doc.bank_message = response["message"]

        doc.save(ignore_permissions=True)

        return response

    except Exception as e:
        doc.status = "Failed"

        if hasattr(e, "response") and e.response is not None:
            try:
                error = e.response.json()

                doc.response_json = json.dumps(error, indent=2)

                doc.bank_reference = error.get("reference")
                doc.bank_message = error.get("message")

            except ValueError:
                doc.response_json = e.response.text

        else:
            doc.response_json = str(e)

        doc.save(ignore_permissions=True)
        raise

def build_payload(doc, source):
    payload = {
        "source": {
            "countryCode": source.country_code,
            "name": source.account_name,
            "accountNumber": source.account_number,
        },
        "sender": {
            "name": doc.sender_name,
            "documentType": doc.sender_document_type,
            "documentNumber": doc.sender_document_number,
            "countryCode": doc.sender_country_code,
            "mobileNumber": doc.sender_mobile_number,
            "email": doc.sender_email,
            "address": doc.sender_address,
        },
        "destination": {},
        "transfer": {
            "amount": str(doc.amount),
            "currencyCode": doc.currency,
            "reference": generate_reference(),
            "date": today(),
            "description": doc.description,
        },
    }

    transfer_type = doc.transfer_type

    if transfer_type == "Internal Bank":

        payload["destination"] = {
            "type": "bank",
            "countryCode": doc.recipient_country,
            "name": doc.recipient_name,
            "bankCode": doc.bank_code,
            "accountNumber": doc.recipient_account_number,
            "mobileNumber": doc.recipient_mobile,
            "documentType": doc.recipient_document_type,
            "documentNumber": doc.recipient_document_number,
            "email": doc.recipient_email,
            "address": doc.recipient_address,
        }

        payload["transfer"]["type"] = "InternalFundsTransfer"

    elif transfer_type == "Mobile Wallet":

        payload["destination"] = {
            "type": "mobile",
            "countryCode": doc.recipient_country,
            "name": doc.recipient_name,
            "mobileNumber": doc.recipient_mobile_number,
            "walletName": doc.recipient_wallet_name,
            "documentType": doc.recipient_document_type,
            "documentNumber": doc.recipient_document_number,
        }

        payload["transfer"]["type"] = "MobileWallet"

    elif transfer_type == "Pesalink Account":

        payload["destination"] = {
            "type": "bank",
            "countryCode": doc.destination_country_code,
            "name": doc.destination_name,
            "bankCode": doc.destination_bank_code,
            "accountNumber": doc.destination_account_number,
            "mobileNumber": doc.destination_mobile_number,
            "documentType": doc.destination_document_type,
            "documentNumber": doc.destination_document_number,
        }

        payload["transfer"]["type"] = "Pesalink"

    elif transfer_type == "Pesalink Mobile":

        payload["destination"] = {
            "type": "mobile",
            "countryCode": doc.destination_country_code,
            "name": doc.destination_name,
            "bankCode": doc.destination_bank_code,
            "mobileNumber": doc.destination_mobile_number,
            "documentType": doc.destination_document_type,
            "documentNumber": doc.destination_document_number,
        }

        payload["transfer"]["type"] = "Pesalink"

    else:
        frappe.throw(f"Unsupported IMT transfer type: {transfer_type}")
    return payload