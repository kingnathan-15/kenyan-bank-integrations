# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BankTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		currency: DF.Data
		description: DF.SmallText
		destination_account: DF.Link
		destination_balance_after: DF.Currency
		destination_balance_before: DF.Currency
		reference: DF.Data
		request_json: DF.Code | None
		response_json: DF.Code | None
		source_account: DF.Link
		source_balance_after: DF.Currency
		source_balance_before: DF.Currency
		status: DF.Literal["Draft", "Processing", "Successful", "Failed"]
		transfer_type: DF.Literal["EFT", "RTGS", "Pesalink"]
	# end: auto-generated types

	pass
