import frappe
from frappe import _
from frappe.utils import getdate

from banking_integration.clients.jenga import JengaClient
from banking_integration.clients.stanbic import StanbicClient
from banking_integration.services.providers import get_bank_account_credentials


def sync_jenga_statement(bank_account, from_date, to_date):
    """
    Fetch a Jenga bank statement and synchronize it into
    the Account Statement DocType.

    Existing transactions are skipped using the Jenga reference
    as the Account Statement document name.
    """

    if isinstance(bank_account, str):
        bank_account = frappe.get_doc("Bank Account", bank_account)

    if not bank_account:
        frappe.throw(_("Bank Account is required"))

    if not bank_account.bank_account_no:
        frappe.throw(
            _("Bank Account {0} has no account number").format(bank_account.name)
        )

    credentials = get_bank_account_credentials(bank_account)

    if not credentials:
        frappe.throw(
            _("No Bank Integration Credentials found for {0}").format(bank_account.bank)
        )

    client = JengaClient(credentials=credentials)

    payload = {
        "accountNumber": bank_account.bank_account_no.strip(),
        "countryCode": "KE",
        "fromDate": str(from_date),
        "toDate": str(to_date),
        "limit": 100,
        "reference": "",
        "serial": "",
        "postedDateTime": "",
        "date": "",
        "runningBalance": {
            "currency": "",
            "amount": 0.0,
        },
    }

    result = client.fetch_statement(payload)

    if not result:
        frappe.throw(_("Jenga returned an empty response"))

    if not result.get("status"):
        frappe.throw(
            _("Jenga statement request failed: {0}").format(
                result.get("message") or "Unknown error"
            )
        )

    data = result.get("data") or {}
    transactions = data.get("transactions") or []

    created = 0
    skipped = 0
    failed = 0

    for transaction in transactions:
        reference = transaction.get("reference")

        if not reference:
            failed += 1
            continue

        reference = str(reference).strip()

        if frappe.db.exists("Account Statement", reference):
            skipped += 1
            continue

        running_balance = transaction.get("runningBalance") or {}

        statement = frappe.get_doc(
            {
                "doctype": "Account Statement",
                "name": reference,
                "account": bank_account.name,
                "reference": reference,
                "date": _parse_datetime(
                    transaction.get("date") or transaction.get("postedDateTime")
                ),
                "amount": transaction.get("amount") or 0,
                "serial": transaction.get("serial"),
                "description": transaction.get("description"),
                "type": transaction.get("type"),
                "new_amount": running_balance.get("amount") or 0,
                "currency": (
                    running_balance.get("currency") or data.get("currency") or "KES"
                ),
                "transaction_id": transaction.get("transactionId"),
            }
        )

        statement.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()

    return {
        "status": True,
        "message": "Statement synchronized successfully",
        "account": bank_account.name,
        "account_number": bank_account.bank_account_no,
        "currency": data.get("currency"),
        "balance": data.get("balance"),
        "transactions_returned": len(transactions),
        "created": created,
        "skipped": skipped,
        "failed": failed,
    }


def sync_stanbic_statement(account, date_from, date_to):
    bank_account = frappe.get_doc("Bank Account", account)

    account_number = bank_account.bank_account_no

    if not account_number:
        frappe.throw(
            f"Bank Account {account} does not have an account number."
        )

    client = StanbicClient(
        credentials=get_bank_account_credentials(bank_account)
    )

    payload = {
        "bookingDateGreaterThan": date_from,
        "bookingDateLessThan": date_to,
        "accountNumber": account_number,
    }

    response = client.fetch_transactions(payload)

    if not response or not response.get("success"):
        frappe.throw("Stanbic transaction request failed.")

    transactions = response.get("data", {}).get(
        "transaction-items", []
    )

    created = skipped = 0

    for tx in transactions:
        tx_id = tx.get("id") or tx.get("reference")

        if not tx_id or frappe.db.exists(
            "Account Statement",
            {"transaction_id": tx_id},
        ):
            skipped += 1
            continue

        amount_data = tx.get(
            "transactionAmountCurrency", {}
        )

        amount = amount_data.get("amount")

        if amount is None:
            skipped += 1
            continue

        indicator = tx.get("creditDebitIndicator")

        statement = frappe.new_doc("Account Statement")

        statement.update({
            "account": bank_account.name,
            "reference": tx.get("reference") or tx_id,
            "date": getdate(tx.get("bookingDate")),
            "amount": abs(float(amount)),
            "serial": tx_id,
            "description": (
                tx.get("description")
                or tx.get("category")
                or ""
            ),
            "type": (
                "Credit"
                if indicator == "CRDT"
                else "Debit"
                if indicator == "DBIT"
                else None
            ),
            "currency": amount_data.get("currencyCode"),
            "transaction_id": tx_id,
        })

        statement.insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()

    return {
        "status": "success",
        "account": account_number,
        "transactions": len(transactions),
        "created": created,
        "skipped": skipped,
    }

def _parse_datetime(value):
    """
    Convert Jenga's ISO datetime into a Frappe-compatible datetime.
    """

    if not value:
        return None

    try:
        return frappe.utils.get_datetime(value)
    except Exception:
        return None
