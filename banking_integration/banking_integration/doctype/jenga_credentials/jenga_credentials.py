# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class JengaCredentials(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		access_token: DF.SmallText | None
		api_key: DF.Password
		consumer_secret: DF.Password
		environment: DF.Literal["Sandbox", "Production"]
		merchant_code: DF.Password
		private_key: DF.LongText
		public_key: DF.LongText | None
		token_expiry: DF.Datetime | None
	# end: auto-generated types

	pass
