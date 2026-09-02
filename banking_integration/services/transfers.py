# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import today

from banking_integration.clients.jenga import JengaClient
from banking_integration.clients.stanbic import StanbicClient
from banking_integration.clients.kcb import KCBClient
from banking_integration.services.balances import refresh_balance
from banking_integration.services.providers import (
    get_bank_account_credentials,
)
from banking_integration.utils.reference import generate_reference


STANBIC_ENDPOINT_MAP = {
    "Pesalink Bank": "/api/sandbox/payments/pesalink",
    "Pesalink Mobile": "/api/sandbox/payments/pesalink/mobile",
    "RTGS": "/api/sandbox/payments/rtgs",
    "Mobile Wallet": "/api/sandbox/payments/mobile",
    "B2C": "/api/sandbox/payments/b2c",
    "STK Push": "/api/sandbox/payments/stkpush",
}


# =====================================================================
# MAIN TRANSFER DISPATCHER
# =====================================================================


def send_money(bank_transfer: str):
    """
    Send an approved Bank Transfer through its configured provider.

    Bank Transfer is the ERP tracking document.
    The actual money movement is performed by the configured
    banking provider.
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
    "Equity Bank Kenya": _send_via_jenga,
    "Stanbic Bank Kenya": _send_via_stanbic,
    "KCB Bank Kenya": _send_via_kcb,
    "Equity Bank": _send_via_jenga,
    "Stanbic Bank": _send_via_stanbic,
    "Kenya Commercial Bank": _send_via_kcb,
}.get(doc.bank)

    if not dispatcher:
        frappe.throw(
            _(
                "Unsupported bank: {0}"
            ).format(
                doc.bank
            )
        )

    # Prevent accidental double submission.
    if doc.status in (
        "Processing",
        "Successful",
    ):
        frappe.throw(
            _(
                "Bank Transfer {0} has already been submitted."
            ).format(
                doc.name
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


# =====================================================================
# JENGA
# =====================================================================


def _send_via_jenga(doc):
    """
    Dispatch a Bank Transfer to the correct Jenga transaction API.

    Each transaction type has its own payload builder and its own
    JengaClient method.
    """

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

    # ---------------------------------------------------------------
    # Internal Bank Transfer
    # ---------------------------------------------------------------

    if doc.transfer_type == "Internal Bank Transfer":

        response = _jenga_internal_transfer(
            client=client,
            doc=doc,
            source=source,
            reference=reference,
        )

    # ---------------------------------------------------------------
    # RTGS
    # ---------------------------------------------------------------

    elif doc.transfer_type == "RTGS":

        payload = _build_jenga_rtgs_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.rtgs_transfer(
            payload
        )

    # ---------------------------------------------------------------
    # Pesalink - Bank Account
    # ---------------------------------------------------------------

    elif doc.transfer_type == "Pesalink Bank":

        payload = _build_jenga_pesalink_account_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.pesalink_account_transfer(
            payload
        )

    # ---------------------------------------------------------------
    # Pesalink - Mobile
    # ---------------------------------------------------------------

    elif doc.transfer_type == "Pesalink Mobile":

        payload = _build_jenga_pesalink_mobile_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.pesalink_mobile_transfer(
            payload
        )

    # ---------------------------------------------------------------
    # Mobile Wallet
    # ---------------------------------------------------------------

    elif doc.transfer_type == "Mobile Wallet":

        payload = _build_jenga_mobile_wallet_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.mobile_wallet_transfer(
            payload
        )

    # ---------------------------------------------------------------
    # SWIFT
    # ---------------------------------------------------------------

    elif doc.transfer_type == "SWIFT":

        payload = _build_jenga_swift_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.swift_transfer(
            payload
        )

    # ---------------------------------------------------------------
    # Subsidiary
    # ---------------------------------------------------------------

    elif doc.transfer_type == "Subsidiary":

        payload = _build_jenga_subsidiary_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        doc.request_json = frappe.as_json(
            payload,
            indent=2,
        )

        response = client.subsidiary_transfer(
            payload
        )

    else:

        frappe.throw(
            _(
                "Jenga transfer type {0} is not supported."
            ).format(
                doc.transfer_type
            )
        )

    # ---------------------------------------------------------------
    # Save API response
    # ---------------------------------------------------------------

    doc.response_json = frappe.as_json(
        response,
        indent=2,
    )

    doc.bank_reference = (
        response.get("reference")
        or response.get("transactionId")
        or response.get("data", {}).get("transactionId")
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


# =====================================================================
# JENGA - INTERNAL BANK TRANSFER
# =====================================================================


def _jenga_internal_transfer(
    client,
    doc,
    source,
    reference,
):
    """
    Build and send an internal transfer between Equity/Jenga
    supported bank accounts.
    """

    destination = frappe.get_doc(
        "Bank Account",
        doc.destination_account,
    )

    # ---------------------------------------------------------------
    # Capture currently stored balances
    # ---------------------------------------------------------------

    doc.source_balance_before = (
        source.custom_reported_balance
    )


    # ---------------------------------------------------------------
    # Build payload
    # ---------------------------------------------------------------

    payload = {
        "source": {
            "countryCode": _get_country_code(source),
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "bank",
            "countryCode": _get_country_code(destination),
            "name": destination.account_name,
            "accountNumber": destination.bank_account_no,
        },
        "transfer": {
            "type": "InternalFundsTransfer",
            "amount": str(doc.amount),
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

    # ---------------------------------------------------------------
    # Send transfer
    # ---------------------------------------------------------------

    response = client.internal_bank_transfer(
        payload
    )

    # ---------------------------------------------------------------
    # Refresh balances AFTER successful transfer
    # ---------------------------------------------------------------

    if response.get("status") is True:

        try:
            refresh_balance(source.name)
            refresh_balance(destination.name)

            # Reload because refresh_balance() saves the documents
            source.reload()
            destination.reload()

            doc.source_balance_after = (
                source.custom_reported_balance
            )

        except Exception:
            frappe.log_error(
                frappe.get_traceback(),
                "Jenga Internal Transfer - Balance Refresh Failed",
            )

    return response

# =====================================================================
# JENGA - RTGS
# =====================================================================


def _build_jenga_rtgs_payload(
    doc,
    source,
    reference,
):
    """
    Build the payload required by Jenga RTGS.
    """

    return {
        "source": {
            "countryCode": _get_country_code(source),
            "currency": doc.currency,
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },

        "destination": {
            "type": "bank",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "bankCode": doc.bank_code,
            "accountNumber": doc.beneficiary_account_number,
        },

        "transfer": {
            "type": "RTGS",
            "amount": str(doc.amount),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
            "purposeOfPaymentCode": (
                doc.purpose_of_payment_code
                if getattr(
                    doc,
                    "purpose_of_payment_code",
                    None,
                )
                else "OTHR"
            ),
        },
    }

# =====================================================================
# JENGA - PESALINK BANK ACCOUNT
# =====================================================================


def _build_jenga_pesalink_account_payload(
    doc,
    source,
    reference,
):
    """
    Build Pesalink-to-bank-account payload.
    """

    return {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "currency": doc.currency,
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "bank",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "bankCode": doc.bank_code,
            "accountNumber": doc.beneficiary_account_number,
        },
        "transfer": {
            "type": "Pesalink",
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }


# =====================================================================
# JENGA - PESALINK MOBILE
# =====================================================================


def _build_jenga_pesalink_mobile_payload(
    doc,
    source,
    reference,
):
    """
    Build Pesalink-to-mobile-number payload.
    """

    return {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "currency": doc.currency,
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "mobile",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "mobileNumber": doc.beneficiary_mobile_number,
        },
        "transfer": {
            "type": "PesalinkMobile",
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }


# =====================================================================
# JENGA - MOBILE WALLET
# =====================================================================


def _build_jenga_mobile_wallet_payload(
    doc,
    source,
    reference,
):
    """
    Build mobile-wallet transfer payload.
    """

    return {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "currency": doc.currency,
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "mobile",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "mobileNumber": doc.beneficiary_mobile_number,
            "walletName": doc.wallet_name,
        },
        "transfer": {
            "type": "MobileWallet",
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }


# =====================================================================
# JENGA - SWIFT
# =====================================================================


def _build_jenga_swift_payload(
    doc,
    source,
    reference,
):
    """
    Build the Jenga SWIFT transfer payload.
    """

    source_currency = frappe.db.get_value(
        "Account",
        source.account,
        "account_currency",
    )

    if not source_currency:
        frappe.throw(
            _(
                "Could not determine the currency for source Account {0}."
            ).format(
                source.account
            )
        )

    return {
        "source": {
            "countryCode": _get_country_code(source),
            "sourceCurrency": source_currency,
            "name": doc.sender_name or source.account_name,
            "accountNumber": source.bank_account_no,
        },

        "destination": {
            "type": "bank",
            "countryCode": doc.beneficiary_country,
            "currency": doc.destination_currency,
            "name": doc.beneficiary_name,
            "bankBic": doc.bank_bic,
            "accountNumber": doc.beneficiary_account_number,
            "addressline1": doc.beneficiary_address,
        },

        "transfer": {
            "type": "SWIFT",
            "amount": str(doc.amount),
            "currencyCode": doc.destination_currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }

# =====================================================================
# JENGA - SUBSIDIARY
# =====================================================================


def _build_jenga_subsidiary_payload(
    doc,
    source,
    reference,
):
    """
    Build Equity subsidiary transfer payload.
    """

    return {
        "source": {
            "countryCode": _get_country_code(
                source
            ),
            "currency": doc.currency,
            "name": source.account_name,
            "accountNumber": source.bank_account_no,
        },
        "destination": {
            "type": "bank",
            "countryCode": doc.beneficiary_country,
            "name": doc.beneficiary_name,
            "bankCode": doc.bank_code,
            "accountNumber": doc.beneficiary_account_number,
        },
        "transfer": {
            "type": "Subsidiary",
            "amount": str(
                doc.amount
            ),
            "currencyCode": doc.currency,
            "reference": reference,
            "date": today(),
            "description": doc.description,
        },
    }


# =====================================================================
# STANBIC
# =====================================================================

def _send_via_stanbic(doc):
    """
    Send a Bank Transfer through Stanbic.

    The payment rail is determined by doc.transfer_type and mapped
    to the corresponding Stanbic sandbox API.
    """

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

    # ---------------------------------------------------------------
    # Stanbic payment rail
    # ---------------------------------------------------------------

    if doc.transfer_type == "EFT":

        payload = _build_stanbic_eft_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/eft-payments/"

    elif doc.transfer_type == "Pesalink Bank":

        payload = _build_stanbic_pesalink_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/pesalink-payments/"

    elif doc.transfer_type == "RTGS":

        payload = _build_stanbic_rtgs_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/rtgs-payments/"

    elif doc.transfer_type == "B2C":

        payload = _build_stanbic_b2c_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/stanbic-payments/"

    elif doc.transfer_type == "Mobile Wallet":

        payload = _build_stanbic_mobile_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/mobile-payments/"

    elif doc.transfer_type == "STK Push":

        payload = _build_stanbic_stk_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/mpesa-checkout/"

    elif doc.transfer_type == "Internal Bank Transfer":

        payload = _build_stanbic_internal_transfer_payload(
            doc=doc,
            source=source,
            reference=reference,
        )

        endpoint = "/api/sandbox/inter-account-transfer/"

    else:

        frappe.throw(
            _(
                "Transfer Type {0} is not supported for Stanbic."
            ).format(
                doc.transfer_type
            )
        )

    # ---------------------------------------------------------------
    # Store request
    # ---------------------------------------------------------------

    doc.request_json = frappe.as_json(
        payload,
        indent=2,
    )

    # ---------------------------------------------------------------
    # Send request
    # ---------------------------------------------------------------

    result = client.post(
        endpoint,
        payload,
    )

    # ---------------------------------------------------------------
    # Store response
    # ---------------------------------------------------------------

    doc.response_json = frappe.as_json(
        result,
        indent=2,
    )

    response_data = result.get(
        "data",
        {},
    )

    doc.bank_reference = (
        response_data.get("dbsReferenceId")
        or response_data.get("bankReferenceId")
        or response_data.get("transactionId")
        or response_data.get("reference")
        or reference
    )

    doc.status = (
        "Successful"
        if result.get("success")
        else "Failed"
    )

    doc.save(ignore_permissions=True)

    frappe.db.commit()

    return result

def _build_stanbic_eft_payload(
    doc,
    source,
    reference,
):
    return {
        "SourceChannel": "BCBC",
        "SourceMsgId": reference,
        "CreatedTime": frappe.utils.now_datetime().strftime(
            "%H:%M"
        ),
        "DebitAccount": source.bank_account_no,
        "DBPUniqueTransactionNumber": reference,
        "BeneficiaryAcctNo": doc.beneficiary_account_number,
        "BeneficiaryName": doc.beneficiary_name,
        "BeneficiaryBankCode": doc.bank_code or "17000",
        "BeneficiaryAddr": "Nairobi",
        "ExchangeRate": "",
        "CreditAmount": str(doc.amount),
        "CreditCurrency": doc.currency or "KES",
        "PaymentDetails": (
            doc.description or "EFT Payment"
        )[:35],
        "FxDealId": "",
        "Execute": "1",
        "PaymentType": "SBK.BCB.EFT.CREDIT",
        "ExecutionDate": frappe.utils.today(),
        "Attachments": [],
    }

def _build_stanbic_rtgs_payload(
    doc,
    source,
    reference,
):
    """
    Build the Stanbic RTGS payment payload.
    """

    return {
        "originatorAccount": {
            "identification": {
                "identification": source.bank_account_no,
                "debitCurrency": doc.currency or "KES",
                "mobileNumber": (
                    doc.sender_mobile_number
                    or ""
                ),
            }
        },

        "requestedExecutionDate": (
            frappe.utils.today()
        ),

        "dbsReferenceId": reference,

        "txnNarrative": (
            doc.description
            or "RTGS Payment"
        ),

        "callBackUrl": frappe.utils.get_url(
            "/api/method/banking_integration.banking_integration.api.callbacks.stanbic.handle_payment_notification"
        ),

        "transferTransactionInformation": {
            "instructedAmount": {
                "amount": str(doc.amount),
                "creditCurrency": (
                    doc.currency or "KES"
                ),
            },

            "counterpartyAccount": {
                "identification": {
                    "identification": (
                        doc.beneficiary_account_number
                    ),
                    "beneficiaryBank": (
                        doc.bank_code or ""
                    ),
                    "beneficiaryChargeType": "SHA",
                }
            },

            "counterparty": {
                "name": doc.beneficiary_name,

                "postalAddress": {
                    "addressLine": (
                        doc.beneficiary_address
                        or "KENYA"
                    ),
                    "postCode": "00100",
                    "town": "Nairobi",
                    "country": (
                        doc.beneficiary_country
                        or "KE"
                    ),
                }
            },

            "remittanceInformation": {
                "type": "UNSTRUCTURED",
                "content": (
                    doc.description
                    or "RTGS Payment"
                ),
            },

            "endToEndIdentification": reference,
        },
    }

# =====================================================================
# KCB
# =====================================================================

def _send_via_kcb(doc):

    source = frappe.get_doc(
        "Bank Account",
        doc.source_account,
    )

    credentials = get_bank_account_credentials(
        source
    )

    client = KCBClient(
        credentials=credentials
    )

    reference = (
        doc.transaction_reference
        or generate_reference()
    )

    # KCB allows a maximum of 12 characters
    reference = reference[:12]

    doc.transaction_reference = reference

    payload = _build_kcb_funds_transfer_payload(
        doc=doc,
        source=source,
        reference=reference,
    )

    doc.request_json = frappe.as_json(
        payload,
        indent=2,
    )

    response = client.funds_transfer(
        payload
    )

    doc.response_json = frappe.as_json(
        response,
        indent=2,
    )

    header = response.get(
        "header",
        {},
    )

    doc.bank_reference = (
        header.get("retrievalRefNumber")
        or header.get("messageID")
    )

    doc.status = (
        "Successful"
        if header.get("statusCode") == "0"
        else "Failed"
    )

    doc.save(
        ignore_permissions=True
    )

    frappe.db.commit()

    return response



def _build_kcb_funds_transfer_payload(doc, source, reference):
    # Using hardcoded values for the sandbox until whitelisted.
    # Later, companyCode can be moved to Bank Integration Credentials.
    return {
        "companyCode": "KE0010001", 
        "transactionType": "IF",
        "debitAccountNumber": source.bank_account_no, # Ensure this is the whitelisted one
        "creditAccountNumber": doc.beneficiary_account_number,
        "debitAmount": float(doc.amount),
        "paymentDetails": doc.description[:35], 
        "transactionReference": reference,
        "currency": doc.currency,
        "beneficiaryDetails": doc.beneficiary_name[:35], # Enforcing KCB's 35 char limit
        "beneficiaryBankCode": doc.bank_code,
    }
# =====================================================================
# HELPERS
# =====================================================================


def _get_country_code(bank_account):
    """
    Return the country code configured on the Bank Account.
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