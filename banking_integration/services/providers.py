import frappe


def get_bank_credentials(bank, environment=None):
    """
    Get integration credentials for an ERPNext Bank.

    The Bank Integration Credentials record is matched using
    the `bank` field.
    """

    if isinstance(bank, str):
        bank = frappe.get_doc("Bank", bank)

    if not bank:
        frappe.throw("Bank is required")

    filters = {
        "bank": bank.name,
    }

    if environment:
        filters["environment"] = environment

    credentials_name = frappe.db.get_value(
        "Bank Integration Credentials",
        filters,
        "name",
    )

    if not credentials_name:
        frappe.throw(
            f"No integration credentials found for Bank {bank.name}"
            + (
                f" in {environment} environment"
                if environment
                else ""
            )
        )

    return frappe.get_doc(
        "Bank Integration Credentials",
        credentials_name,
    )


def get_bank_account_credentials(bank_account):
    """
    Get integration credentials from the Bank linked to a Bank Account.

    Bank Account -> Bank -> Bank Integration Credentials
    """

    if isinstance(bank_account, str):
        bank_account = frappe.get_doc(
            "Bank Account",
            bank_account,
        )

    if not bank_account.bank:
        frappe.throw(
            f"Bank Account {bank_account.name} has no Bank configured"
        )

    return get_bank_credentials(
        bank_account.bank,
    )