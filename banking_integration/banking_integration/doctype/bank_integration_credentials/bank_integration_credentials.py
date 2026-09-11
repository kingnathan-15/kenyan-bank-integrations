# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BankIntegrationCredentials(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from banking_integration.banking_integration.doctype.bank_api_keys.bank_api_keys import BankAPIKeys
		from frappe.types import DF

		access_token: DF.SmallText | None
		account_number: DF.Data | None
		api_key: DF.Password | None
		bank: DF.Link
		bank_keys: DF.Table[BankAPIKeys]
		client_id: DF.Data | None
		client_secret: DF.Password | None
		consumer_secret: DF.Password | None
		environment: DF.Literal["Sandbox", "Production"]
		has_multiple_auths: DF.Check
		merchant_code: DF.Password | None
		private_key: DF.LongText | None
		production_url: DF.Data | None
		public_key: DF.LongText | None
		sandbox_url: DF.Data | None
		token_expiry: DF.Datetime | None
		webhook_secret: DF.Password | None
	# end: auto-generated types

	pass
