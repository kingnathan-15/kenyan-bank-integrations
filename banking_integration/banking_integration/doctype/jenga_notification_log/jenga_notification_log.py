# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class JengaNotificationLog(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		error: DF.SmallText | None
		notification_type: DF.Literal[None]
		payload: DF.Code | None
		processed: DF.Check
		received_on: DF.Datetime | None
		reference: DF.Data | None
		status: DF.Literal["Received", "Processed", "Failed"]
	# end: auto-generated types

	pass
