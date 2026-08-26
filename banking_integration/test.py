import time
import frappe
from banking_integration.services.kcb import KCBClient

def test_kcb_funds_transfer():
    # 1. Fetch Sandbox Credentials directly
    credentials_name = frappe.db.get_value(
        "Bank Integration Credentials",
        {"bank": "KCB Bank Kenya", "environment": "Sandbox"}
    )

    if not credentials_name:
        print("❌ No Sandbox credentials found for KCB Bank Kenya.")
        return

    credentials = frappe.get_doc("Bank Integration Credentials", credentials_name)
    print(f"✅ Loaded credentials: {credentials.name}")

    # 2. Instantiate the client
    client = KCBClient(credentials=credentials)

    # 3. Construct the hardcoded payload
    # Generating a dynamic 12-character reference using a timestamp
    reference = str(int(time.time()))[-12:]

    payload = {
        "companyCode": "KE0010001",
        "transactionType": "IF",
        "debitAccountNumber": "37890012", 
        "creditAccountNumber": "909099090",
        "debitAmount": 10.0,
        "paymentDetails": "fee payment",
        "transactionReference": reference,
        "currency": "KES",
        "beneficiaryDetails": "JOHN DOE",
        "beneficiaryBankCode": "01"
    }

    print("🚀 Sending payload to KCB:")
    print(frappe.as_json(payload))

    # 4. Execute the transfer
    try:
        response = client.funds_transfer(payload)
        
        print("\n📥 Raw KCB Response:")
        print(frappe.as_json(response))

        # 5. Evaluate success strictly via the header
        header = response.get("header", {})
        status_code = header.get("statusCode")

        if status_code == "0":
            print(f"\n✅ SUCCESS! Transaction processed.")
            print(f"Bank Reference: {header.get('retrievalRefNumber')}")
        else:
            print(f"\n⚠️ FAILED (HTTP 200, but transaction failed).")
            print(f"Status Code: {status_code}")
            print(f"Message: {header.get('statusMessage')}")

    except Exception as e:
        print(f"\n❌ EXCEPTION OCCURRED: {str(e)}")