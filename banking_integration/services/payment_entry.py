import frappe
from frappe import _

from banking_integration.banking_integration.doctype.bank_transfer.bank_transfer import (
    create_from_reference,
)


ALLOWED_TRANSFER_TYPES = {
    "EFT",
    "RTGS",
    "Pesalink Bank",
    "Pesalink Mobile",
    "SWIFT",
    "Mobile Wallet",
    "Internal Bank Transfer",
}


@frappe.whitelist()
def create_bank_transfer_from_payment_entry(doc, method=None):

    if isinstance(doc, str):
        doc = frappe.get_doc("Payment Entry", doc)

    if doc.docstatus != 1:
        return

    # ---------------------------------------------------------
    # Prevent duplicate Bank Transfer
    # ---------------------------------------------------------

    existing = frappe.db.exists(
        "Bank Transfer",
        {
            "reference_doctype": "Payment Entry",
            "reference_name": doc.name,
        },
    )

    if existing:
        return existing

    # ---------------------------------------------------------
    # Validate source Bank Account
    # ---------------------------------------------------------

    if not doc.bank_account:
        frappe.throw(
            _("Company Bank Account is required.")
        )

    source_account = frappe.db.get_value(
        "Bank Account",
        {
            "name": doc.bank_account,
            "company": doc.company,
        },
        "name",
    )

    if not source_account:
        frappe.throw(
            _("Bank Account {0} was not found.").format(
                doc.bank_account
            )
        )

    # ---------------------------------------------------------
    # Validate party
    # ---------------------------------------------------------

    if not doc.party:
        frappe.throw(
            _("Party is required.")
        )

    # ---------------------------------------------------------
    # Find destination Bank Account
    # ---------------------------------------------------------

    destination_account = get_party_bank_account(
        party_type=doc.party_type,
        party=doc.party,
    )

    if not destination_account:
        frappe.throw(
            _(
                "No Bank Account found for {0} {1}."
            ).format(
                doc.party_type,
                doc.party,
            )
        )

    # ---------------------------------------------------------
    # Load Bank Accounts
    # ---------------------------------------------------------

    source = frappe.get_doc(
        "Bank Account",
        source_account,
    )

    destination = frappe.get_doc(
        "Bank Account",
        destination_account,
    )

    # ---------------------------------------------------------
    # Provider
    # ---------------------------------------------------------

    provider = get_provider(source)

    if not provider:
        frappe.throw(
            _(
                "No banking provider configured for {0}."
            ).format(
                source.name
            )
        )

    # ---------------------------------------------------------
    # Transfer type
    # ---------------------------------------------------------

    transfer_type = get_transfer_type(doc)

    # ---------------------------------------------------------
    # Description
    # ---------------------------------------------------------

    description = (
        doc.remarks
        or _("Payment to {0}").format(
            doc.party_name or doc.party
        )
    )

    # ---------------------------------------------------------
    # Create using the Bank Transfer's official mechanism
    # ---------------------------------------------------------

    transfer = create_from_reference(
        reference_doctype="Payment Entry",
        reference_name=doc.name,

        provider=provider,

        source_account=source.name,
        destination_account=destination.name,

        transfer_type=transfer_type,

        amount=doc.paid_amount,
        currency=doc.paid_from_account_currency,

        description=description,

        sender_name=doc.company,
        sender_country_code="KE",

        beneficiary_name=(
            doc.party_name or doc.party
        ),
        beneficiary_country="KE",

        beneficiary_account_number=(
            destination.bank_account_no
        ),
    )

    return transfer.name


def get_party_bank_account(
    party_type,
    party,
):
    """
    Find the Bank Account belonging to the party.
    """

    return frappe.db.get_value(
        "Bank Account",
        {
            "party_type": party_type,
            "party": party,
        },
        "name",
    )


def get_provider(bank_account):
    """
    Get the banking integration provider configured
    on the Bank Account.
    """

    return frappe.db.get_value(
        "Bank Account",
        bank_account.name,
        "custom_provider",
    )


def get_transfer_type(payment_entry):

    transfer_type = payment_entry.get(
        "custom_bank_transfer_type"
    )

    if not transfer_type:
        frappe.throw(
            _(
                "Bank Transfer Type has not been selected."
            )
        )

    if transfer_type not in ALLOWED_TRANSFER_TYPES:
        frappe.throw(
            _(
                "Invalid Bank Transfer Type: {0}"
            ).format(
                transfer_type
            )
        )

    return transfer_type


def on_payment_entry_cancel(
    doc,
    method=None,
):
    """
    Prevent cancellation if money has already been sent.
    """

    linked_transfers = frappe.get_all(
        "Bank Transfer",
        filters={
            "reference_doctype": "Payment Entry",
            "reference_name": doc.name,
        },
        fields=[
            "name",
            "status",
        ],
    )

    for transfer in linked_transfers:

        if transfer.status in (
            "Processing",
            "Successful",
        ):

            frappe.throw(
                _(
                    "Cannot cancel Payment Entry {0}. "
                    "Bank Transfer {1} is currently {2}. "
                    "Funds may have already moved."
                ).format(
                    doc.name,
                    frappe.utils.get_link_to_form(
                        "Bank Transfer",
                        transfer.name,
                    ),
                    transfer.status,
                )
            )