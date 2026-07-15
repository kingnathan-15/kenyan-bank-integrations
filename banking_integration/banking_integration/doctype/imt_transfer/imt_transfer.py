# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class IMTTransfer(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amount: DF.Currency
		bank_code: DF.Data | None
		bank_reference: DF.Data | None
		currency: DF.Data
		description: DF.SmallText
		mobile_number: DF.Data | None
		recipient_account_number: DF.Data | None
		recipient_address: DF.SmallText | None
		recipient_country: DF.Data
		recipient_document_number: DF.Data
		recipient_document_type: DF.Literal["National Id", "Passport", "Alien Id", "Driving License"]
		recipient_email: DF.Data | None
		recipient_mobile: DF.Data | None
		recipient_name: DF.Data
		reference: DF.Data | None
		request_json: DF.Code | None
		response_json: DF.Code | None
		sender_address: DF.SmallText | None
		sender_country_code: DF.Data | None
		sender_document_number: DF.Data
		sender_document_type: DF.Literal["National Id", "Passport", "Alien Id", "Driving License"]
		sender_email: DF.Data | None
		sender_mobile_number: DF.Data
		sender_name: DF.Data
		source_account: DF.Link
		status: DF.Literal["Draft", "Processing", "Successful", "Failed", "Pending"]
		transaction_date: DF.Date
		transfer_type: DF.Literal["Internal Bank", "Mobile Wallet", "Pesalink Account", "Pesalink Mobile"]
		wallet_name: DF.Literal["Mpesa", "AirtelMoney", "Equitel", "TKash"]
	# end: auto-generated types

	pass
