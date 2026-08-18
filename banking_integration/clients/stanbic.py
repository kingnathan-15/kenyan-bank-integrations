# Copyright (c) 2026, Nathan Wagacha and contributors
# For license information, please see license.txt

import frappe
import requests


class StanbicClient:
    """
    Client for Stanbic API.

    Uses the shared Bank Integration Credentials DocType.
    """

    AUTH_PATH = "/api/sandbox/auth/oauth2/token"

    def __init__(self, credentials):
        self.credentials = credentials

        if credentials.environment == "Sandbox":
            self.base_url = (
                credentials.sandbox_url
                or "https://sandbox.connect.stanbicbank.co.ke"
            ).rstrip("/")
        else:
            self.base_url = (
                credentials.production_url
                or ""
            ).rstrip("/")

        if not self.base_url:
            frappe.throw(
                "Stanbic credentials: No API URL configured."
            )

    # ------------------------------------------------------------------
    # AUTHENTICATION
    # ------------------------------------------------------------------

    def get_access_token(self, force_refresh=False):
        """
        Return a valid Stanbic OAuth access token.

        If the stored token is still valid, reuse it.
        If it is expired or force_refresh=True, request a new
        token from Stanbic and save it.
        """

        now = frappe.utils.now_datetime()

        # 1. Existing token is still valid
        if (
            not force_refresh
            and self.credentials.access_token
            and self.credentials.token_expiry
            and self.credentials.token_expiry > now
        ):
            return self.credentials.access_token

        # 2. Token doesn't exist or has expired.
        #    Generate a new one from Stanbic.

        client_id = self.credentials.client_id
        client_secret = self.credentials.get_password("client_secret")

        if not client_id:
            frappe.throw("Stanbic Client ID is missing.")

        if not client_secret:
            frappe.throw("Stanbic Client Secret is missing.")

        payload = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": "payments",
        }

        response = requests.post(
            f"{self.base_url}{self.AUTH_PATH}",
            data=payload,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            timeout=30,
        )

        if response.status_code != 200:
            frappe.log_error(
                title="Stanbic OAuth Error",
                message=(
                    f"Status: {response.status_code}\n"
                    f"Response: {response.text}"
                ),
            )

            frappe.throw(
                f"Stanbic authentication failed: HTTP {response.status_code}"
            )

        data = response.json()

        access_token = data.get("access_token")

        if not access_token:
            frappe.throw(
                f"Stanbic did not return an access token: {data}"
            )

        expires_in = int(
            data.get("expires_in", 3600)
        )

        # 3. Save the newly generated token
        self.credentials.access_token = access_token

        # Refresh 60 seconds before actual expiry
        self.credentials.token_expiry = frappe.utils.add_to_date(
            now,
            seconds=max(expires_in - 60, 60),
            as_datetime=True,
        )

        self.credentials.save(
            ignore_permissions=True
        )

        frappe.db.commit()

        return access_token

    def request(
        self,
        method,
        endpoint,
        payload=None,
        retry_on_401=True,
    ):
        """
        Make an authenticated Stanbic API request.
        """

        token = self.get_access_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        response = requests.request(
            method,
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        # Token may have expired server-side
        if (
            response.status_code == 401
            and retry_on_401
        ):
            token = self.get_access_token(
                force_refresh=True
            )

            headers["Authorization"] = (
                f"Bearer {token}"
            )

            response = requests.request(
                method,
                url,
                headers=headers,
                json=payload,
                timeout=30,
            )

        try:
            data = response.json()
        except ValueError:
            data = {
                "raw_text": response.text
            }

        return {
            "status_code": response.status_code,
            "data": data,
            "success": response.status_code in (
                200,
                201,
                202,
            ),
        }

    def get(self, endpoint):
        return self.request(
            "GET",
            endpoint,
        )

    def post(self, endpoint, payload):
        return self.request(
            "POST",
            endpoint,
            payload=payload,
        )