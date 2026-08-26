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

            credentials = self._get_credentials(
                bank_account
            )

        else:
            frappe.throw(
                "Bank Account or Bank Integration Credentials is required"
            )

        self.credentials = credentials

        if credentials.environment == "Sandbox":
            self.base_url = credentials.sandbox_url
        else:
            self.base_url = credentials.production_url

        self.api_key = credentials.get_password(
            "api_key"
        )

        self.merchant_code = credentials.get_password(
            "merchant_code"
        )

        self.consumer_secret = credentials.get_password(
            "consumer_secret"
        )

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------
    def _get_credentials(self, bank_account):

        provider = bank_account.bank

        if not provider:
            frappe.throw(
                f"Bank Account {bank_account.name} "
                "has no integration provider configured"
            )

        credentials = frappe.db.get_value(
            "Bank Integration Credentials",
            {
                "Bank": provider,
                "environment": "Sandbox",
            },
            "name",
        )

        if not credentials:
            frappe.throw(
                f"No Bank Integration Credentials found "
                f"for provider {provider}"
            )

        return frappe.get_doc(
            "Bank Integration Credentials",
            credentials,
        )
    
    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def generate_token(self):

        url = (
            f"{self.base_url}"
            "/authentication/api/v3/authenticate/merchant"
        )

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

        token = response.json().get(
            "accessToken"
        )

        if not token:
            frappe.throw(
                "Jenga authentication response "
                "did not contain an access token"
            )

        return token

    # ------------------------------------------------------------------
    # Generic request
    # ------------------------------------------------------------------

    def request(
        self,
        method,
        endpoint,
        **kwargs
    ):

        token = self.generate_token()

        headers = kwargs.pop(
            "headers",
            {}
        )

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

    # ------------------------------------------------------------------
    # Balance
    # ------------------------------------------------------------------

    def get_balance(
        self,
        account_number,
        country_code="KE"
    ):

        account_number = account_number.strip()

        token = self.generate_token()

        signature_string = (
            f"{country_code}"
            f"{account_number}"
        )

        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        response = requests.get(
            (
                f"{self.base_url}"
                "/v3-apis/account-api/v3.0/accounts/balances/"
                f"{country_code}/{account_number}"
            ),
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------------------------
    # Statement
    # ------------------------------------------------------------------

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
            (
                f"{self.base_url}"
                "/v3-apis/account-api/v3.0/accounts/fullStatement"
            ),
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

    # ------------------------------------------------------------------
    # Account Inquiry
    # ------------------------------------------------------------------

    def account_inquiry(
        self,
        account_number,
        country_code="KE"
    ):

        account_number = account_number.strip()

        token = self.generate_token()

        signature_string = (
            f"{country_code}"
            f"{account_number}"
        )

        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        response = requests.get(
            (
                f"{self.base_url}"
                "/v3-apis/account-api/v3.0/search/"
                f"{country_code}/{account_number}"
            ),
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    # ------------------------------------------------------------------
    # Internal Bank Transfer
    # ------------------------------------------------------------------

    def internal_bank_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["source"]["accountNumber"]
            + str(payload["transfer"]["amount"])
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/internalBankTransfer"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # RTGS
    # ------------------------------------------------------------------

    def rtgs_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["transfer"]["reference"]
            + payload["transfer"]["date"]
            + payload["source"]["accountNumber"]
            + payload["destination"]["accountNumber"]
            + str(payload["transfer"]["amount"])
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/rtgs"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # Pesalink - Bank Account
    # ------------------------------------------------------------------

    def pesalink_account_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["source"]["accountNumber"]
            + str(payload["transfer"]["amount"])
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/pesalinkacc"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # Pesalink - Mobile Number
    # ------------------------------------------------------------------

    def pesalink_mobile_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["source"]["accountNumber"]
            + str(payload["transfer"]["amount"])
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/pesalinkMobile"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # Mobile Wallet
    # ------------------------------------------------------------------

    def mobile_wallet_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["source"]["accountNumber"]
            + str(payload["transfer"]["amount"])
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/sendmobile"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # SWIFT
    # ------------------------------------------------------------------

    def swift_transfer(self, payload):
        signature_string=(
            payload["transfer"]["reference"]
            + payload["transfer"]["date"]
            + payload["source"]["accountNumber"]
            + payload["destination"]["accountNumber"]
            + payload["transfer"]["amount"]
        )    
        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/swift"
            ),
            payload=payload,
            signature_string=signature_string,
        )
    # ------------------------------------------------------------------
    # Subsidiary Transfer
    # ------------------------------------------------------------------

    def subsidiary_transfer(
        self,
        payload
    ):

        signature_string = (
            payload["source"]["accountNumber"]
            + str(payload["transfer"]["amount"])
            + payload["transfer"]["currencyCode"]
            + payload["transfer"]["reference"]
        )

        return self._send_remittance(
            endpoint=(
                "/v3-apis/transaction-api/v3.0/"
                "remittance/subsidiary"
            ),
            payload=payload,
            signature_string=signature_string,
        )

    # ------------------------------------------------------------------
    # Shared Remittance HTTP Request
    # ------------------------------------------------------------------

    def _send_remittance(
        self,
        endpoint,
        payload,
        signature_string
    ):

        token = self.generate_token()

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
            f"{self.base_url}{endpoint}",
            headers=headers,
            data=json.dumps(
                payload,
                separators=(",", ":"),
            ),
            timeout=30,
        )

        if not response.ok:
            frappe.throw(
                f"Jenga API Error {response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    def fetch_statement(self, payload):

        print("\n" + "=" * 60)
        print("JENGA STATEMENT REQUEST")
        print("=" * 60)

        # ---------------------------------------------------------
        # Request details
        # ---------------------------------------------------------

        account_number = payload["accountNumber"]
        country_code = payload["countryCode"]
        to_date = payload["toDate"]

        print(f"[1/6] Account: {account_number}")
        print(f"[1/6] Date range: {payload['fromDate']} → {to_date}")

        # ---------------------------------------------------------
        # Authentication
        # ---------------------------------------------------------

        print("[2/6] Generating Jenga access token...")

        token = self.generate_token()

        print("[2/6] ✓ Access token generated")

        # ---------------------------------------------------------
        # Signature
        # ---------------------------------------------------------

        print("[3/6] Generating request signature...")

        signature_string = (
            f"{account_number}"
            f"{country_code}"
            f"{to_date}"
        )

        signature = generate_signature(
            signature_string,
            self.credentials.private_key,
        )

        print("[3/6] ✓ Signature generated")

        # ---------------------------------------------------------
        # Request
        # ---------------------------------------------------------

        url = (
            f"{self.base_url}"
            "/v3-apis/account-api/v3.0/accounts/fullStatement"
        )

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "signature": signature,
        }

        print("[4/6] Sending request to Jenga...")
        print(f"[4/6] URL: {url}")

        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(
                payload,
                separators=(",", ":"),
                sort_keys=True,
            ),
            timeout=30,
        )

        print(
            f"[5/6] Jenga response: "
            f"HTTP {response.status_code}"
        )

        # ---------------------------------------------------------
        # Error handling
        # ---------------------------------------------------------

        if not response.ok:

            print("[5/6] ✗ Jenga request failed")
            print(f"[5/6] Response: {response.text}")

            response.raise_for_status()

        print("[5/6] ✓ Jenga request successful")

        # ---------------------------------------------------------
        # Parse response
        # ---------------------------------------------------------

        result = response.json()

        print("[6/6] Response parsed successfully")

        print("\n" + "=" * 60)
        print("JENGA STATEMENT RESULT")
        print("=" * 60)

        print(f"Status: {result.get('status')}")
        print(f"Code: {result.get('code')}")
        print(f"Message: {result.get('message')}")

        data = result.get("data", {})

        print(f"Account: {data.get('accountNumber')}")
        print(f"Currency: {data.get('currency')}")
        print(f"Balance: {data.get('balance')}")

        transactions = data.get(
            "transactions",
            [],
        )

        print(f"Transactions returned: {len(transactions)}")

        print("=" * 60)

        return result