# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today

from banking_integration.clients.jenga import JengaClient
from banking_integration.clients.stanbic import StanbicClient
from banking_integration.services.balances import refresh_balance
from banking_integration.services.providers import (
    get_bank_account_credentials,
)
from banking_integration.utils.reference import generate_reference


JENGA_TRANSFER_TYPE_MAP = {
    "EFT": "InternalFundsTransfer",
    "RTGS": "InternalFundsTransfer",
    "Pesalink Bank": "Pesalink",
    "Pesalink Mobile": "Pesalink",
    "SWIFT": "InternationalRemittance",
    "Mobile Wallet": "MobileWallet",
}


STANBIC_ENDPOINT_MAP = {
    "Pesalink Bank": "/api/sandbox/payments/pesalink",
    "Pesalink Mobile": "/api/sandbox/payments/pesalink/mobile",
    "RTGS": "/api/sandbox/payments/rtgs",
    "Mobile Wallet": "/api/sandbox/payments/mobile",
    "B2C": "/api/sandbox/payments/b2c",
    "STK Push": "/api/sandbox/payments/stkpush",
}


def send_money(bank_transfer: str):
    """
    Send an approved Bank Transfer through its configured provider.

    Bank Transfer is a tracking document. The actual source account
    is always an ERPNext Bank Account.
    """

    doc = frappe.get_doc(
        "Bank Transfer",
        bank_transfer,
    )

    if doc.status != "Approved":
        frappe.throw(
            _(
                "Bank Transfer must be Approved before it can be sent."
            )
        )

    dispatcher = {
        "Jenga": _send_via_jenga,
        "Stanbic": _send_via_stanbic,
    }.get(doc.provider)

    if not dispatcher:
        frappe.throw(
            _(
                "Unsupported provider: {0}"
            ).format(
                doc.provider
            )
        )

    doc.status = "Processing"
    doc.save(
        ignore_permissions=True
    )

    try:
        dispatcher(doc)

    except Exception as e:
        doc.status = "Failed"

        doc.response_json = frappe.as_json(
            {
                "error": str(e),
            },
            indent=2,
        )

        doc.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        raise

    return doc


# ---------------------------------------------------------------------
# Jenga
# ---------------------------------------------------------------------


def _send_via_jenga(doc):
    source = frappe.get_doc(
        "Bank Account",
        doc.source_account,
    )

    credentials = get_bank_account_credentials(
        source
    )

    client = JengaClient(
        credentials=credentials
    )

    reference = (
        doc.transaction_reference
        or generate_reference()
    )

    doc.transaction_reference = reference

    if doc.transfer_type == "Internal Bank Transfer":
        response = _jenga_internal_transfer(
            client=client,
            doc=doc,
            source=source,
            reference=reference,
        )

    else:
        payload = _build_jenga_external_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.send_transfer(
            payload
        )

    doc.response_json = frappe.as_json(
        response,
        indent=2,
    )

    doc.bank_reference = (
        response.get("reference")
        or response.get("transactionId")
    )

    doc.status = (
        "Successful"
        if response.get("status") is True
        else "Failed"
    )

    doc.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return response


def _jenga_internal_transfer(
    client,
    doc,
    source,
    reference,
):
    destination = frappe.get_doc(
        "Bank Account",
        doc.destination_account,
    )

    refresh_balance(
        source
    )

    refresh_balance(
        destination
    )

    doc.source_balance_before = (
        source.custom_reported_balance
    )

    doc.destination_balance_before = (
        destination.custom_reported_balance
    )

    payload = {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "bank",
            "countryCode": _get_country_code(
                destination
            ),
            "name": destination.account_name,
            "accountNumber": destination.bank_account_no,
        },
        "transfer": {
            "type": "InternalFundsTransfer",
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }

    doc.request_json = frappe.as_json(
        payload,
        indent=2,
    )

    response = client.internal_bank_transfer(
        payload
    )

    if response.get("status") is True:
        refresh_balance(
            source
        )

        refresh_balance(
            destination
        )

        doc.source_balance_after = (
            source.custom_reported_balance
        )

        doc.destination_balance_after = (
            destination.custom_reported_balance
        )

    return response


def _build_jenga_external_payload(
    doc,
    source,
    reference,
):
    payload = {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
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
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
            "type": JENGA_TRANSFER_TYPE_MAP.get(
                doc.transfer_type,
                doc.transfer_type,
            ),
        },
    }

    if doc.transfer_type in (
        "Pesalink Mobile",
        "Mobile Wallet",
    ):
        payload["destination"] = {
            "type": "mobile",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "mobileNumber": doc.beneficiary_mobile_number,
            "walletName": doc.wallet_name,
            "documentType": doc.beneficiary_document_type,
            "documentNumber": doc.beneficiary_document_number,
        }

    else:
        payload["destination"] = {
            "type": "bank",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "bankCode": doc.bank_code,
            "accountNumber": doc.beneficiary_account_number,
            "mobileNumber": doc.beneficiary_mobile_number,
            "documentType": doc.beneficiary_document_type,
            "documentNumber": doc.beneficiary_document_number,
            "email": doc.beneficiary_email,
            "address": doc.beneficiary_address,
        }

    return payload


# ---------------------------------------------------------------------
# Stanbic
# ---------------------------------------------------------------------


def _send_via_stanbic(doc):
    source = frappe.get_doc(
        "Bank Account",
        doc.source_account,
    )

    credentials = get_bank_account_credentials(
        source
    )

    client = StanbicClient(
        credentials
    )

    reference = (
        doc.transaction_reference
        or generate_reference()
    )

    doc.transaction_reference = reference

    endpoint = STANBIC_ENDPOINT_MAP.get(
        doc.transfer_type
    )

    if not endpoint:
        frappe.throw(
            _(
                "Transfer Type {0} is not supported for Stanbic."
            ).format(
                doc.transfer_type
            )
        )

    payload = {
        "sourceAccount": source.bank_account_no,
        "beneficiaryName": doc.beneficiary_name,
        "beneficiaryAccount": (
            doc.beneficiary_account_number
        ),
        "bankCode": doc.bank_code,
        "mobileNumber": (
            doc.beneficiary_mobile_number
        ),
        "amount": str(
            doc.amount
        ),
        "currency": doc.currency,
        "narration": doc.description,
        "reference": reference,
    }

    doc.request_json = frappe.as_json(
        payload,
        indent=2,
    )

    result = client.post(
        endpoint,
        payload,
    )

    response_data = result.get(
        "data",
        {},
    )

    doc.response_json = frappe.as_json(
        response_data,
        indent=2,
    )

    doc.bank_reference = (
        response_data.get(
            "transactionId"
        )
        or response_data.get(
            "reference"
        )
    )

    doc.status = (
        "Successful"
        if result.get("success")
        else "Failed"
    )

    doc.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return result


def _get_country_code(bank_account):
    """
    Return the country code used by the banking API.

    `country_code` is expected to be a custom field on
    ERPNext's Bank Account doctype.
    """

    country_code = getattr(
        bank_account,
        "custom_country_code",
        None,
    )

    if not country_code:
        frappe.throw(
            _(
                "Bank Account {0} has no Country Code configured."
            ).format(
                bank_account.name
            )
        )

    return country_code