import uuid

import frappe
import requests


class KCBClient:
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
            self.base_url = (
                credentials.sandbox_url
                or "https://uat.buni.kcbgroup.com"
            )
        else:
            self.base_url = credentials.production_url

        self.client_id = credentials.get_password(
            "client_id"
        )

        self.client_secret = credentials.get_password(
            "client_secret"
        )

    # ------------------------------------------------------------------
    # Credentials
    # ------------------------------------------------------------------

    def _get_credentials(self, bank_account):

        if not bank_account.bank:
            frappe.throw(
                f"Bank Account {bank_account.name} "
                "has no Bank configured"
            )

        credentials_name = frappe.db.get_value(
            "Bank Integration Credentials",
            {
                "bank": bank_account.bank,
                "environment": "Sandbox",
            },
            "name",
        )

        if not credentials_name:
            frappe.throw(
                f"No KCB credentials found for "
                f"{bank_account.bank}"
            )

        return frappe.get_doc(
            "Bank Integration Credentials",
            credentials_name,
        )

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def generate_token(self):

        response = requests.post(
            f"{self.base_url}/token",
            auth=(
                self.client_id,
                self.client_secret,
            ),
            data={
                "grant_type": "client_credentials",
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=30,
        )

        if not response.ok:
            frappe.throw(
                f"KCB authentication failed: "
                f"{response.status_code} "
                f"{response.text}"
            )

        data = response.json()

        token = data.get(
            "access_token"
        )

        if not token:
            frappe.throw(
                "KCB authentication response "
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
            {},
        )

        headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

        response = requests.request(
            method,
            f"{self.base_url}{endpoint}",
            headers=headers,
            timeout=30,
            **kwargs,
        )

        if not response.ok:
            frappe.throw(
                f"KCB API Error "
                f"{response.status_code}: "
                f"{response.text}"
            )

        return response.json()

    # ------------------------------------------------------------------
    # Funds Transfer
    # ------------------------------------------------------------------

    def funds_transfer(self, payload):
        token = self.generate_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"{self.base_url}/fundstransfer/1.0.0/api/v1/transfer",
            headers=headers,
            json=payload,
            timeout=30,
        )

        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            frappe.throw("KCB returned an invalid JSON response")

        if response.status_code >= 400:
            frappe.throw(
                f"KCB API Error {response.status_code}: "
                f"{frappe.as_json(data)}"
            )

        return data