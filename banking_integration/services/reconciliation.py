import frappe
from frappe.utils import getdate, add_days


def reconcile_statement(statement_name):
    statement = frappe.get_doc("Account Statement", statement_name)

    if statement.reconciliation_status == "Matched":
        return {
            "status": "already_matched",
            "message": "Statement is already reconciled.",
            "statement": statement.name,
        }

    matches = _find_by_reference(statement)

    if not matches:
        matches = _find_by_amount_and_date(statement)

    if len(matches) == 1:
        match = matches[0]

        statement.db_set(
            "reconciliation_status",
            "Matched",
            update_modified=True,
        )

        statement.db_set(
            "matched_document_type",
            match["doctype"],
            update_modified=True,
        )

        statement.db_set(
            "matched_document",
            match["name"],
            update_modified=True,
        )

        statement.db_set(
            "reconciled_on",
            frappe.utils.now(),
            update_modified=True,
        )

        statement.db_set(
            "reconciled_by",
            frappe.session.user,
            update_modified=True,
        )

        return {
            "status": "matched",
            "statement": statement.name,
            "matched_document_type": match["doctype"],
            "matched_document": match["name"],
        }

    if len(matches) > 1:
        statement.db_set(
            "reconciliation_status",
            "Multiple Matches",
            update_modified=True,
        )

        statement.db_set(
            "reconciled_on",
            frappe.utils.now(),
            update_modified=True,
        )

        statement.db_set(
            "reconciled_by",
            frappe.session.user,
            update_modified=True,
        )

        return {
            "status": "multiple_matches",
            "statement": statement.name,
            "matches": matches,
        }

    statement.db_set(
        "reconciliation_status",
        "Unmatched",
        update_modified=True,
    )

    statement.db_set(
        "matched_document_type",
        None,
        update_modified=True,
    )

    statement.db_set(
        "matched_document",
        None,
        update_modified=True,
    )

    statement.db_set(
        "reconciled_on",
        frappe.utils.now(),
        update_modified=True,
    )

    statement.db_set(
        "reconciled_by",
        frappe.session.user,
        update_modified=True,
    )

    return {
        "status": "unmatched",
        "statement": statement.name,
        "message": "No matching ERPNext transaction was found.",
    }


def _find_by_reference(statement):
    matches = []

    reference = statement.reference

    if not reference:
        return matches

    doctypes = [
        "Payment Entry",
        "Journal Entry",
    ]

    for doctype in doctypes:
        if not frappe.db.exists("DocType", doctype):
            continue

        records = frappe.get_all(
            doctype,
            filters={
                "name": reference,
            },
            fields=["name"],
            limit=10,
        )

        for record in records:
            matches.append(
                {
                    "doctype": doctype,
                    "name": record.name,
                }
            )

    return matches


def _find_by_amount_and_date(statement):
    matches = []

    if not statement.amount or not statement.date:
        return matches

    statement_date = getdate(statement.date)

    start_date = add_days(statement_date, -2)
    end_date = add_days(statement_date, 2)

    doctypes = [
        "Payment Entry",
        "Journal Entry",
    ]

    for doctype in doctypes:

        if not frappe.db.exists("DocType", doctype):
            continue

        records = frappe.get_all(
            doctype,
            filters=[
                ["docstatus", "=", 1],
                ["posting_date", ">=", start_date],
                ["posting_date", "<=", end_date],
            ],
            fields=["name", "posting_date"],
        )

        for record in records:
            amount = _get_transaction_amount(
                doctype,
                record.name,
                statement.type,
            )

            if amount is None:
                continue

            if abs(float(amount) - float(statement.amount)) < 0.01:
                matches.append(
                    {
                        "doctype": doctype,
                        "name": record.name,
                    }
                )

    return matches


def _get_transaction_amount(doctype, name, transaction_type):
    if doctype == "Payment Entry":
        payment = frappe.db.get_value(
            "Payment Entry",
            name,
            [
                "payment_type",
                "paid_amount",
                "received_amount",
            ],
            as_dict=True,
        )

        if not payment:
            return None

        if transaction_type == "Credit":
            return payment.received_amount

        return payment.paid_amount

    if doctype == "Journal Entry":
        accounts = frappe.get_all(
            "Journal Entry Account",
            filters={
                "parent": name,
            },
            fields=[
                "debit",
                "credit",
            ],
        )

        if transaction_type == "Credit":
            return sum(
                float(row.credit or 0)
                for row in accounts
            )

        return sum(
            float(row.debit or 0)
            for row in accounts
        )

    return None