import json

import frappe
import requests

from banking_integration.utils.jenga_auth import generate_signature


class JengaClient:
    def __init__(self, bank_account=None, credentials=None):
        if credentials:
            if isinstance(credentials, str):
                credentials = frappe.get_doc(
                    "Bank Integration Credentials",
                    credentials,
                )
        elif bank_account:
            if isinstance(bank_account, str):
                bank_account = frappe.get_doc(
                    "Bank Account",
                    bank_account,
                )

            credentials = self._get_credentials(bank_account)

        else:
            frappe.throw("Bank Account or Bank Integration Credentials is required")

        self.credentials = credentials

        if credentials.environment == "Sandbox":
            self.base_url = credentials.sandbox_url
        else:
            self.base_url = credentials.production_url

        self.api_key = credentials.get_password("api_key")
        self.merchant_code = credentials.get_password("merchant_code")
        self.consumer_secret = credentials.get_password("consumer_secret")

    def _get_credentials(self, bank_account):
        provider = bank_account.custom_provider

        if not provider:
            frappe.throw(
                f"Bank Account {bank_account.name} has no integration provider configured"
            )

        credentials = frappe.db.get_value(
            "Bank Integration Credentials",
            {
                "provider": provider,
                "environment": "Sandbox",
            },
            "name",
        )

        if not credentials:
            frappe.throw(
                f"No Bank Integration Credentials found for provider {provider}"
            )

        return frappe.get_doc(
            "Bank Integration Credentials",
            credentials,
        )

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

        response.raise_for_status()

        token = response.json().get("accessToken")

        if not token:
            frappe.throw(
                "Jenga authentication response did not contain an access token"
            )

        return token

    def request(self, method, endpoint, **kwargs):
        token = self.generate_token()

        headers = kwargs.pop("headers", {})

        headers.update({
            "Authorization": f"Bearer {token}",
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        })

        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=30,
            **kwargs,
        )

        response.raise_for_status()

        return response.json()

    def get_balance(self, account_number, country_code="KE"):
        account_number = account_number.strip()

        token = self.generate_token()

        signature_string = f"{country_code}{account_number}"
        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

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

    def fetch_statement(self, payload):
        token = self.generate_token()

        signature_string = (
            f"{payload['accountNumber']}"
            f"{payload['countryCode']}"
            f"{payload['toDate']}"
        )

        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        response = requests.post(
            f"{self.base_url}/v3-apis/account-api/v3.0/accounts/fullStatement",
            headers=headers,
            data=json.dumps(
                payload,
                separators=(",", ":"),
                sort_keys=True,
            ),
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def internal_bank_transfer(self, payload):
        token = self.generate_token()

        signature_string = (
            payload["source"]["accountNumber"]
            + payload["transfer"]["amount"]
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "signature": signature,
        }

        response = requests.post(
            f"{self.base_url}/v3-apis/transaction-api/v3.0/remittance/internalBankTransfer",
            headers=headers,
            data=json.dumps(
                payload,
                separators=(",", ":"),
            ),
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def account_inquiry(self, account_number, country_code="KE"):
        account_number = account_number.strip()

        token = self.generate_token()

        signature_string = f"{country_code}{account_number}"
        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        response = requests.get(
            f"{self.base_url}/v3-apis/account-api/v3.0/search/"
            f"{country_code}/{account_number}",
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()
