# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BankCallbackLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		bank_transfer: DF.Link | None
		callback_type: DF.Literal[None]
		headers: DF.LongText | None
		payload: DF.JSON | None
		processed: DF.Check
		processing_error: DF.SmallText | None
		retrieval_reference: DF.Data | None
		transaction_reference: DF.Data | None
	# end: auto-generated types
	pass
