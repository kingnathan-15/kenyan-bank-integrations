# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class AccountStatementReference(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		date: DF.Datetime
		description: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		reference: DF.Data | None
		type: DF.Literal["Debit", "Credit"]
	# end: auto-generated types

	pass
