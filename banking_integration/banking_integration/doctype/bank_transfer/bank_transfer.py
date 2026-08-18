# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.password import check_password


ALLOWED_TRANSFER_TYPES = {
    "Jenga": {
        "Internal Bank Transfer",
        "EFT",
        "RTGS",
        "Pesalink Bank",
        "Pesalink Mobile",
        "SWIFT",
        "Mobile Wallet",
    },
    "Stanbic": {
        "Pesalink Bank",
        "Pesalink Mobile",
        "RTGS",
        "Mobile Wallet",
        "B2C",
        "STK Push",
    },
}

ALLOWED_ORIGIN_DOCTYPES = {
    "Payment Entry",
    "Purchase Invoice",
}


class BankTransfer(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        amount: DF.Currency
        approved_by: DF.Link | None
        approved_on: DF.Datetime | None
        bank_code: DF.Data | None
        bank_reference: DF.Data | None
        beneficiary_account_number: DF.Data | None
        beneficiary_address: DF.SmallText | None
        beneficiary_country: DF.Data | None
        beneficiary_document_number: DF.Data | None
        beneficiary_document_type: DF.Data | None
        beneficiary_email: DF.Data | None
        beneficiary_mobile_number: DF.Data | None
        beneficiary_name: DF.Data | None
        currency: DF.Data
        description: DF.SmallText
        destination_account: DF.Link | None
        destination_balance_after: DF.Currency
        destination_balance_before: DF.Currency
        provider: DF.Link
        reference_doctype: DF.Link
        reference_name: DF.DynamicLink
        request_json: DF.Code | None
        response_json: DF.Code | None
        sender_address: DF.SmallText | None
        sender_country_code: DF.Data | None
        sender_document_number: DF.Data | None
        sender_document_type: DF.Data | None
        sender_email: DF.Data | None
        sender_mobile_number: DF.Data | None
        sender_name: DF.Data | None
        source_account: DF.Link
        source_balance_after: DF.Currency
        source_balance_before: DF.Currency
        status: DF.Literal["Draft", "Pending Approval", "Approved", "Processing", "Successful", "Failed"]
        transaction_reference: DF.Data | None
        transfer_type: DF.Literal["Internal Bank Transfer", "EFT", "RTGS", "Pesalink Bank", "Pesalink Mobile", "SWIFT", "Mobile Wallet"]
        wallet_name: DF.Data | None
    # end: auto-generated types
    def validate(self):
        self.validate_origin()
        self.validate_provider_transfer_type()
        self.validate_source_account()
        self.validate_amount()

        if not self.currency and self.source_account:
            self.currency = (
                frappe.db.get_value(
                    "Bank Account",
                    self.source_account,
                    "account_currency",
                )
                or "KES"
            )

    def validate_origin(self):
        if self.reference_doctype not in ALLOWED_ORIGIN_DOCTYPES:
            frappe.throw(
                _(
                    "Bank Transfer must originate from a Payment Entry "
                    "or Purchase Invoice."
                )
            )

        if self.is_new() and not frappe.flags.get("in_bank_transfer_factory"):
            frappe.throw(
                _(
                    "Bank Transfer records cannot be created directly. "
                    "Use the transfer action from the originating "
                    "Payment Entry or Purchase Invoice."
                )
            )

        if not self.reference_name:
            frappe.throw(
                _("A reference document is required.")
            )

        if not frappe.db.exists(
            self.reference_doctype,
            self.reference_name,
        ):
            frappe.throw(
                _(
                    "Reference document {0} {1} does not exist."
                ).format(
                    self.reference_doctype,
                    self.reference_name,
                )
            )

    def validate_provider_transfer_type(self):
        if not self.provider:
            frappe.throw(
                _("A provider is required.")
            )

        allowed = ALLOWED_TRANSFER_TYPES.get(
            self.provider,
            set(),
        )

        if self.transfer_type not in allowed:
            frappe.throw(
                _(
                    "Transfer Type {0} is not supported by provider {1}."
                ).format(
                    frappe.bold(self.transfer_type),
                    frappe.bold(self.provider),
                )
            )

    def validate_source_account(self):
        if not self.source_account:
            frappe.throw(
                _("A source Bank Account is required.")
            )

        if not frappe.db.exists(
            "Bank Account",
            self.source_account,
        ):
            frappe.throw(
                _(
                    "Source Bank Account {0} does not exist."
                ).format(
                    self.source_account
                )
            )

    def validate_amount(self):
        if not self.amount or self.amount <= 0:
            frappe.throw(
                _("Amount must be greater than zero.")
            )


def create_from_reference(
    reference_doctype: str,
    reference_name: str,
    **kwargs,
) -> "BankTransfer":
    """
    Create a Bank Transfer tracking record from an approved
    Payment Entry or Purchase Invoice.

    This is the only supported creation path for Bank Transfer.
    """

    if reference_doctype not in ALLOWED_ORIGIN_DOCTYPES:
        frappe.throw(
            _(
                "Unsupported origin document type: {0}"
            ).format(
                reference_doctype
            )
        )

    if not frappe.db.exists(
        reference_doctype,
        reference_name,
    ):
        frappe.throw(
            _(
                "Reference document {0} {1} does not exist."
            ).format(
                reference_doctype,
                reference_name,
            )
        )

    frappe.flags.in_bank_transfer_factory = True

    try:
        doc = frappe.new_doc("Bank Transfer")

        doc.reference_doctype = reference_doctype
        doc.reference_name = reference_name

        doc.update(kwargs)

        doc.insert(
            ignore_permissions=True
        )

    finally:
        frappe.flags.in_bank_transfer_factory = False

    return doc


@frappe.whitelist()
def approve_and_send(
    bank_transfer: str,
    password: str,
):
    """
    Re-authenticate the current user and send
    an existing Bank Transfer tracking record.
    """

    check_password(
        frappe.session.user,
        password,
    )

    doc = frappe.get_doc(
        "Bank Transfer",
        bank_transfer,
    )

    if doc.status not in (
        "Draft",
        "Pending Approval",
    ):
        frappe.throw(
            _(
                "Only Draft or Pending Approval "
                "transfers can be sent."
            )
        )

    doc.approved_by = frappe.session.user
    doc.approved_on = frappe.utils.now_datetime()
    doc.status = "Approved"

    doc.save(
        ignore_permissions=True
    )

    from banking_integration.services.transfers import send_money

    return send_money(
        doc.name
    )