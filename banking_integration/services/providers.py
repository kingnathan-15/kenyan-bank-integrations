import frappe


def get_provider_credentials(provider, environment=None):
    if not provider:
        frappe.throw("Bank Integration Provider is required")

    filters = {
        "provider": provider,
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
            f"No credentials found for provider {provider}"
            + (f" in {environment} environment" if environment else "")
        )

    return frappe.get_doc(
        "Bank Integration Credentials",
        credentials_name,
    )


def get_bank_account_credentials(bank_account):
    if isinstance(bank_account, str):
        bank_account = frappe.get_doc(
            "Bank Account",
            bank_account,
        )

    if not bank_account.custom_provider:
        frappe.throw(
            f"Bank Account {bank_account.name} has no integration provider configured"
        )

    return get_provider_credentials(
        bank_account.custom_provider,
    )