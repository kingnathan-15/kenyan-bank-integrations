import requests
import frappe

from banking_integration.utils.jenga_auth import generate_signature

class JengaClient:
    SANDBOX_URL = "https://uat.finserve.africa"
    PRODUCTION_URL = "https://api.finserve.africa"

    def __init__(self):
        settings = frappe.get_single("Jenga Credentials")

        if settings.environment == "Sandbox":
            self.base_url = self.SANDBOX_URL
        else:
            self.base_url = self.PRODUCTION_URL
    
        self.api_key = settings.get_password("api_key")
        self.merchant_code = settings.get_password("merchant_code")
        self.consumer_secret = settings.get_password("consumer_secret")

    def generate_token(self):

        url = f"{self.base_url}/authentication/api/v3/authenticate/merchant"

        headers = {
            "Content-Type": "application/json",
            "Api-Key": self.api_key,
        }

        payload = {
            "merchantCode": self.merchant_code,
            "consumerSecret": self.consumer_secret,
        }
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )
        
        print("Status:", response.status_code)
        print("Response:", response.text)
        return response.json().get("accessToken")
    
    def request(self, method, endpoint, **kwargs):

        settings = frappe.get_single("Jenga Credentials")

        token = settings.access_token

        headers = kwargs.pop("headers", {})

        headers.update({
            "Authorization": f"Bearer {token}",
            "Api-Key": self.api_key,
            "Content-Type": "application/json"
        })

        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=30,
            **kwargs
        )

        response.raise_for_status()

        return response.json()
    
    def get_balance(self, account_number, country_code="KE"):

        token = self.generate_token()
        account_number = account_number.strip()

        signature_string = f"{country_code}{account_number}"
        signature = generate_signature(signature_string)

        headers = {
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        response = requests.get(
            f"{self.base_url}/v3-apis/account-api/v3.0/accounts/balances/"
            f"{country_code}/{account_number}",
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()
    
    def internal_bank_transfer(self, payload):

        token = self.generate_token()

        url = (
            f"{self.base_url}"
            "/v3-apis/transaction-api/v3.0/remittance/internalBankTransfer"
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "signature": signature,
            "Content-Type": "application/json",
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()