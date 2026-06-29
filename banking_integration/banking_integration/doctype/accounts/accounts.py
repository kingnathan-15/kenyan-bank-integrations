# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Accounts(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		account_name: DF.Data | None
		account_number: DF.Data
		bank_name: DF.Literal["Equity"]
		country_code: DF.Data
		currency: DF.Data
		current_balance: DF.Currency
		enabled: DF.Check
		last_synced: DF.Datetime | None
	# end: auto-generated types

	pass
