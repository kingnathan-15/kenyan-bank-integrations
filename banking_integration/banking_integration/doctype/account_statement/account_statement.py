# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AccountStatement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account: DF.Link | None
		amount: DF.Float
		currency: DF.Data | None
		date: DF.Datetime | None
		description: DF.SmallText | None
		matched_document: DF.DynamicLink | None
		matched_document_type: DF.Literal["Payment Entry", "Journal Entry", "Bank Transaction", "Bank Transfer"]
		new_amount: DF.Currency
		reconciled_by: DF.Link | None
		reconciled_on: DF.Datetime | None
		reconciliation_status: DF.Literal["Unmatched", "Matched", "Manually Matched"]
		reference: DF.Data | None
		serial: DF.Data | None
		transaction_id: DF.Data | None
		type: DF.Data | None
	# end: auto-generated types

	pass
