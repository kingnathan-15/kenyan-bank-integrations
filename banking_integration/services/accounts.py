import frappe
from frappe.utils import add_years, today, flt, get_datetime
from banking_integration.clients.jenga import JengaClient

@frappe.whitelist()
def sync_statement(account: str) -> dict:
    account_doc = frappe.get_doc("Accounts", account)

    from_date = add_years(today(), -1)   # One year ago
    to_date = today()                    # Today's date

    payload = {
        "countryCode": account_doc.country_code,
        "accountNumber": account_doc.account_number,
        "fromDate": from_date,
        "toDate": to_date,
    }

    response = JengaClient().fetch_statement(payload)
    statements = response.get("data", {}).get("transactions", [])

    imported = 0
    already_exists = 0  # Counter for records skipped because they already exist

    for txn in statements:
        tx_id = str(txn.get("transactionId"))
        
        # Check if transaction already exists via field or document name
        if frappe.db.exists("Account Statement", {"transaction_id": tx_id}) or frappe.db.exists("Account Statement", tx_id):
            already_exists += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Account Statement",
                "name": tx_id, 
                "account": account_doc.name,
                "reference": txn.get("reference"),
                "date": get_datetime(txn.get("date")),
                "amount": flt(txn.get("amount")),
                "serial": txn.get("serial"),
                "description": txn.get("description"),
                "type": txn.get("type"),
                "new_amount": flt(txn.get("runningBalance", {}).get("amount")),
                "currency": txn.get("runningBalance", {}).get("currency"),
                "transaction_id": tx_id,
            })
            
            doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
            imported += 1
            
        except frappe.DuplicateEntryError:
            already_exists += 1
            continue
    
    recent_txns = frappe.get_all(
        "Account Statement",
        filters={"account": account_doc.name},
        fields=["date", "reference", "description", "amount", "type"],
        order_by="date desc",
        limit=10
    )

    # Clear out whatever old data was in the child table visual field
    account_doc.set("recent_statements", [])

    # Append the fresh top 10 rows into the child table framework
    for tx in recent_txns:
        account_doc.append("recent_statements", {
            "date": tx.date,
            "reference": tx.reference,
            "description": tx.description,
            "amount": tx.amount,
            "type": tx.type
        })

    # Save the parent Accounts document to persist the updated table display
    account_doc.save(ignore_permissions=True)

    if imported > 0:
        frappe.db.commit()

    return {
        "status": "success",
        "imported": imported,
        "already_exists": already_exists
    }