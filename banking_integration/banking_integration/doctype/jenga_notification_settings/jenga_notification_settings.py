# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class JengaNotificationSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		base_url: DF.Data | None
		credit_alert_endpoint: DF.Data | None
		deposit_endpoint: DF.Data | None
		enabled: DF.Check
		payment_confirmation_endpoint: DF.Data | None
		transaction_status_endpoint: DF.Data | None
	# end: auto-generated types

	pass
